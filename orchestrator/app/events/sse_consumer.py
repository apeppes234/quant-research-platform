"""Managed Agents SSE consumer.

Implements the Phase 1 load-bearing patterns from docs/10:
stream-first, reconnect-with-consolidation, and the idle-break gate.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from contextlib import nullcontext
from typing import Any

from .schema import event_id, is_terminal_event, normalize_event
from .ws_relay import SessionRelay


class ManagedAgentsEventConsumer:
    def __init__(self, sdk_client: Any, relay: SessionRelay):
        self._client = sdk_client
        self._relay = relay

    async def consume_session(
        self,
        session_id: str,
        *,
        opened: asyncio.Event | None = None,
    ) -> None:
        loop = asyncio.get_running_loop()
        await asyncio.to_thread(self._consume_sync, session_id, loop, opened)

    def _consume_sync(
        self,
        session_id: str,
        loop: asyncio.AbstractEventLoop,
        opened: asyncio.Event | None,
    ) -> None:
        seen: set[str] = set()
        backoff_seconds = 1.0

        while True:
            try:
                terminal = self._consume_once(session_id, seen, loop, opened)
                if terminal:
                    return
                backoff_seconds = 1.0
            except Exception as exc:  # pragma: no cover - network/API failure path
                self._publish(
                    session_id,
                    {
                        "id": f"orchestrator.error:{time.time_ns()}",
                        "type": "orchestrator.error",
                        "kind": "relay.error",
                        "processedAt": None,
                        "payload": {"message": str(exc)},
                    },
                    loop,
                )
                time.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 30.0)

    def _consume_once(
        self,
        session_id: str,
        seen: set[str],
        loop: asyncio.AbstractEventLoop,
        opened: asyncio.Event | None,
    ) -> bool:
        if self._client.raw is None:
            raise RuntimeError("Anthropic SDK client is not configured")
        events_api = self._client.raw.beta.sessions.events

        stream_obj = events_api.stream(session_id=session_id)
        stream_context = stream_obj if hasattr(stream_obj, "__enter__") else nullcontext(stream_obj)

        with stream_context as stream:
            if opened is not None and not opened.is_set():
                loop.call_soon_threadsafe(opened.set)

            if self._handle_history(events_api, session_id, seen, loop):
                return True

            for raw_event in stream:
                self._handle_event(session_id, raw_event, seen, loop)
                if is_terminal_event(raw_event):
                    return True

        return False

    def _handle_history(
        self,
        events_api: Any,
        session_id: str,
        seen: set[str],
        loop: asyncio.AbstractEventLoop,
    ) -> bool:
        response = events_api.list(session_id=session_id)
        for raw_event in _iter_page_data(response):
            self._handle_event(session_id, raw_event, seen, loop)
            if is_terminal_event(raw_event):
                return True
        return False

    def _handle_event(
        self,
        session_id: str,
        raw_event: Any,
        seen: set[str],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        raw_id = event_id(raw_event)
        if raw_id is not None:
            if raw_id in seen:
                return
            seen.add(raw_id)

        normalized = normalize_event(raw_event)
        if normalized is not None:
            self._publish(session_id, normalized, loop)

    def _publish(
        self,
        session_id: str,
        event: dict[str, Any],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        future = asyncio.run_coroutine_threadsafe(self._relay.publish(session_id, event), loop)
        future.result(timeout=10)


def _iter_page_data(response: Any) -> Iterable[Any]:
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    if data is None:
        return []
    return data
