"""Session lifecycle and event sending for Managed Agents runs."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from ..clients.anthropic_client import ManagedAgentsClient
from ..config import Settings
from ..events.sse_consumer import ManagedAgentsEventConsumer
from ..events.ws_relay import SessionRelay


class SessionManager:
    def __init__(
        self,
        *,
        settings: Settings,
        client: ManagedAgentsClient,
        relay: SessionRelay,
    ):
        self._settings = settings
        self._client = client
        self._relay = relay
        self._consumer = ManagedAgentsEventConsumer(client, relay)
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._opened: dict[str, asyncio.Event] = {}
        self._vault_ids_by_name: dict[str, str] = {}
        self._memory_store_ids_by_name: dict[str, str] = {}

    async def create_session(self) -> str:
        self._settings.require_session_config()
        vault_ids = await self._session_vault_ids()
        resources = await self._session_resources()
        response = await asyncio.to_thread(
            self._client.create_session,
            agent_id=self._settings.research_manager_agent_id,
            environment_id=self._settings.managed_environment_id,
            vault_ids=vault_ids,
            resources=resources,
        )
        session_id = _get_id(response)
        await self.ensure_stream(session_id)
        return session_id

    async def ensure_stream(self, session_id: str) -> None:
        task = self._tasks.get(session_id)
        opened = self._opened.get(session_id)
        if task is not None and not task.done() and opened is not None:
            await asyncio.wait_for(opened.wait(), timeout=15)
            return

        opened = asyncio.Event()
        self._opened[session_id] = opened
        self._tasks[session_id] = asyncio.create_task(
            self._consumer.consume_session(session_id, opened=opened)
        )
        await asyncio.wait_for(opened.wait(), timeout=15)

    async def send_user_message(self, session_id: str, content: str) -> None:
        await self.ensure_stream(session_id)
        await self._send_event(
            session_id,
            {
                "type": "user.message",
                "content": [{"type": "text", "text": content}],
            },
        )

    async def define_outcome(
        self,
        session_id: str,
        *,
        description: str,
        rubric: str,
        max_iterations: int = 3,
    ) -> None:
        await self.ensure_stream(session_id)
        await self._send_event(
            session_id,
            {
                "type": "user.define_outcome",
                "description": description,
                "rubric": {"type": "text", "content": rubric},
                "max_iterations": max_iterations,
            },
        )

    async def interrupt(self, session_id: str, reason: str | None = None) -> None:
        await self.ensure_stream(session_id)
        await self._send_event(session_id, {"type": "user.interrupt", "reason": reason or "user"})

    async def confirm_tool(
        self,
        session_id: str,
        *,
        tool_use_id: str,
        result: str,
        session_thread_id: str | None = None,
    ) -> None:
        await self.ensure_stream(session_id)
        event: dict[str, Any] = {
            "type": "user.tool_confirmation",
            "tool_use_id": tool_use_id,
            "result": result,
        }
        if session_thread_id:
            event["session_thread_id"] = session_thread_id
        await self._send_event(session_id, event)

    async def _send_event(self, session_id: str, event: dict[str, Any]) -> None:
        await asyncio.to_thread(self._client.send_event, session_id=session_id, event=event)

    async def latest_results(self, session_id: str) -> dict[str, Any] | None:
        files = await asyncio.to_thread(self._client.list_session_files, session_id=session_id)
        results_file = _latest_results_file(files)
        if results_file is None:
            return None
        text = await asyncio.to_thread(
            self._client.download_file_text,
            file_id=_get_id(results_file),
        )
        return json.loads(text)

    async def output_files(self, session_id: str) -> list[dict[str, Any]]:
        files = await asyncio.to_thread(self._client.list_session_files, session_id=session_id)
        return [_file_summary(file) for file in files]

    async def latest_report(self, session_id: str) -> dict[str, Any] | None:
        files = await asyncio.to_thread(self._client.list_session_files, session_id=session_id)
        report_file = _latest_report_file(files)
        if report_file is None:
            return None
        return _file_summary(report_file)

    async def download_output_file(self, session_id: str, file_id: str) -> tuple[dict[str, Any], bytes]:
        files = await asyncio.to_thread(self._client.list_session_files, session_id=session_id)
        match = next((file for file in files if _get_id(file) == file_id), None)
        if match is None:
            raise FileNotFoundError(file_id)
        content = await asyncio.to_thread(self._client.download_file_bytes, file_id=file_id)
        return _file_summary(match), content

    async def _session_vault_ids(self) -> list[str]:
        vault_ids = list(self._settings.vault_id_list)
        if not (self._settings.auto_create_mcp_vaults or self._settings.auto_create_qc_mcp_vault):
            return list(dict.fromkeys(vault_ids))

        for name, url, bearer in [
            ("knowledge", self._settings.mcp_knowledge_url, self._settings.knowledge_mcp_inbound_bearer),
            ("quantconnect", self._settings.mcp_quantconnect_url, self._settings.qc_mcp_inbound_bearer),
            ("fred", self._settings.mcp_fred_url, self._settings.fred_mcp_inbound_bearer),
            ("edgar", self._settings.mcp_edgar_url, self._settings.edgar_mcp_inbound_bearer),
            ("gdelt", self._settings.mcp_gdelt_url, self._settings.gdelt_mcp_inbound_bearer),
            ("arxiv", self._settings.mcp_arxiv_url, self._settings.arxiv_mcp_inbound_bearer),
        ]:
            if not url or not bearer:
                continue
            if name == "quantconnect" and not (
                self._settings.auto_create_qc_mcp_vault or self._settings.auto_create_mcp_vaults
            ):
                continue
            if name not in self._vault_ids_by_name:
                self._vault_ids_by_name[name] = await asyncio.to_thread(
                    self._client.create_static_bearer_vault,
                    display_name=f"quant-research-{name}-mcp",
                    mcp_server_url=url,
                    token=bearer,
                )
            vault_ids.append(self._vault_ids_by_name[name])
        return list(dict.fromkeys(vault_ids))

    async def _session_resources(self) -> list[dict]:
        resources = list(self._settings.memory_store_resources)
        if self._settings.auto_create_memory_stores:
            for name, instructions in [
                (
                    "lessons",
                    "Lessons library: concise notes about strategy ideas that overfit or worked.",
                ),
                (
                    "snooping-ledger",
                    (
                        "Data-snooping ledger: append every variant and optimization run with IS/OOS "
                        "Sharpe and trials_to_date for Deflated Sharpe computation."
                    ),
                ),
            ]:
                if _resource_exists(resources, name):
                    continue
                if name not in self._memory_store_ids_by_name:
                    self._memory_store_ids_by_name[name] = await asyncio.to_thread(
                        self._client.create_memory_store,
                        display_name=f"quant-research-{name}",
                    )
                resources.append(
                    {
                        "type": "memory_store",
                        "memory_store_id": self._memory_store_ids_by_name[name],
                        "access": "read_write",
                        "instructions": instructions,
                    }
                )
        return _dedupe_resources(resources)


def _get_id(response: Any) -> str:
    if isinstance(response, dict) and response.get("id"):
        return str(response["id"])
    value = getattr(response, "id", None)
    if value:
        return str(value)
    raise RuntimeError("Managed Agents session response did not include an id")


def _latest_results_file(files: list[Any]) -> Any | None:
    matches = [file for file in files if _looks_like_results_json(file)]
    if not matches:
        return None
    return sorted(matches, key=_file_sort_key)[-1]


def _latest_report_file(files: list[Any]) -> Any | None:
    matches = [file for file in files if _looks_like_report_pdf(file)]
    if not matches:
        return None
    return sorted(matches, key=_file_sort_key)[-1]


def _looks_like_results_json(file: Any) -> bool:
    values = [
        _get(file, "filename"),
        _get(file, "name"),
        _get(file, "path"),
        _get(file, "display_name"),
    ]
    return any(str(value).endswith("results.json") for value in values if value)


def _looks_like_report_pdf(file: Any) -> bool:
    values = [
        _get(file, "filename"),
        _get(file, "name"),
        _get(file, "path"),
        _get(file, "display_name"),
    ]
    return any(str(value).endswith("report.pdf") for value in values if value)


def _file_summary(file: Any) -> dict[str, Any]:
    filename = (
        _get(file, "filename")
        or _get(file, "name")
        or _get(file, "path")
        or _get(file, "display_name")
        or _get_id(file)
    )
    return {
        "id": _get_id(file),
        "filename": str(filename).rsplit("/", 1)[-1],
        "path": _get(file, "path"),
        "sizeBytes": _get(file, "size_bytes") or _get(file, "size"),
        "mimeType": _get(file, "mime_type") or _get(file, "content_type"),
        "createdAt": _get(file, "created_at"),
    }


def _file_sort_key(file: Any) -> str:
    return str(_get(file, "created_at") or _get(file, "filename") or _get(file, "name") or _get_id(file))


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _resource_exists(resources: list[dict], name: str) -> bool:
    return any(name in str(resource.get("instructions", "")).lower() for resource in resources)


def _dedupe_resources(resources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for resource in resources:
        key = str(resource.get("memory_store_id") or resource)
        if key in seen:
            continue
        seen.add(key)
        unique.append(resource)
    return unique
