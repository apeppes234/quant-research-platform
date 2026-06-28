"""Thin wrapper around the Anthropic beta Managed Agents SDK namespaces."""

from __future__ import annotations

from typing import Any

from ..config import Settings

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - exercised only before deps are installed
    Anthropic = None  # type: ignore[assignment]


class ManagedAgentsClient:
    """Isolate beta SDK calls so route code does not depend on method shapes."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self.raw = None
        if Anthropic is not None and settings.anthropic_api_key:
            self.raw = Anthropic(api_key=settings.anthropic_api_key)

    def create_session(
        self,
        *,
        agent_id: str,
        environment_id: str,
        vault_ids: list[str] | None = None,
        resources: list[dict] | None = None,
    ) -> Any:
        self._require_sdk()
        payload: dict[str, Any] = {
            "agent": agent_id,
            "environment_id": environment_id,
        }
        if vault_ids:
            payload["vault_ids"] = vault_ids
        if resources:
            payload["resources"] = resources
        return self.raw.beta.sessions.create(**payload)

    def send_event(self, *, session_id: str, event: dict[str, Any]) -> Any:
        self._require_sdk()
        send = self.raw.beta.sessions.events.send
        try:
            return send(session_id=session_id, event=event)
        except TypeError:
            return send(session_id=session_id, **event)

    def create_static_bearer_vault(
        self,
        *,
        display_name: str,
        mcp_server_url: str,
        token: str,
    ) -> str:
        self._require_sdk()
        try:
            vault = self.raw.beta.vaults.create(display_name=display_name)
        except TypeError:
            vault = self.raw.beta.vaults.create(name=display_name)
        vault_id = _get_id(vault)
        self.raw.beta.vaults.credentials.create(
            vault_id,
            display_name=f"{display_name} static bearer",
            auth={
                "type": "static_bearer",
                "mcp_server_url": mcp_server_url,
                "token": token,
            },
        )
        return vault_id

    def create_memory_store(self, *, display_name: str) -> str:
        self._require_sdk()
        create = self.raw.beta.memory_stores.create
        try:
            store = create(display_name=display_name)
        except TypeError:
            store = create(name=display_name)
        return _get_id(store)

    def list_session_files(self, *, session_id: str, limit: int = 100) -> list[Any]:
        self._require_sdk()
        page = self.raw.beta.files.list(
            scope_id=session_id,
            limit=limit,
            betas=["managed-agents-2026-04-01"],
        )
        return _page_items(page)

    def download_file_text(self, *, file_id: str) -> str:
        content = self.download_file_bytes(file_id=file_id)
        return content.decode("utf-8")

    def download_file_bytes(self, *, file_id: str) -> bytes:
        self._require_sdk()
        download = self.raw.beta.files.download
        try:
            response = download(file_id, betas=["managed-agents-2026-04-01"])
        except TypeError:
            try:
                response = download(id=file_id, betas=["managed-agents-2026-04-01"])
            except TypeError:
                response = download(file_id=file_id, betas=["managed-agents-2026-04-01"])

        if isinstance(response, bytes):
            return response
        if isinstance(response, bytearray):
            return bytes(response)
        if isinstance(response, str):
            return response.encode("utf-8")

        content = response.read() if hasattr(response, "read") else getattr(response, "content", b"")
        if isinstance(content, bytes):
            return content
        if isinstance(content, bytearray):
            return bytes(content)
        if isinstance(content, str):
            return content.encode("utf-8")
        if hasattr(response, "iter_bytes"):
            return b"".join(response.iter_bytes())
        try:
            return bytes(content)
        except TypeError:
            return str(content).encode("utf-8")

    def _require_sdk(self) -> None:
        if Anthropic is None:
            raise RuntimeError("The anthropic package is not installed. Run `uv sync` in orchestrator/.")
        if not self._settings.anthropic_api_key:
            raise RuntimeError("Missing required Managed Agents configuration: ANTHROPIC_API_KEY")
        if self.raw is None:
            self.raw = Anthropic(api_key=self._settings.anthropic_api_key)


def _get_id(response: Any) -> str:
    if isinstance(response, dict) and response.get("id"):
        return str(response["id"])
    value = getattr(response, "id", None)
    if value:
        return str(value)
    raise RuntimeError("Managed Agents response did not include an id")


def _page_items(response: Any) -> list[Any]:
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    if data is not None:
        return list(data)
    try:
        return list(response)
    except TypeError:
        return []
