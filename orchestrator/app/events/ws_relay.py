"""In-memory websocket fan-out for normalized session events."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class SessionRelay:
    def __init__(self, replay_limit: int = 500):
        self._clients: dict[str, set[WebSocket]] = defaultdict(set)
        self._history: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=replay_limit)
        )
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients[session_id].add(websocket)
            replay = list(self._history[session_id])

        try:
            for event in replay:
                await websocket.send_json(event)
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            async with self._lock:
                self._clients[session_id].discard(websocket)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            self._history[session_id].append(event)
            clients = list(self._clients[session_id])

        stale: list[WebSocket] = []
        for websocket in clients:
            try:
                await websocket.send_json(event)
            except RuntimeError:
                stale.append(websocket)

        if stale:
            async with self._lock:
                for websocket in stale:
                    self._clients[session_id].discard(websocket)
