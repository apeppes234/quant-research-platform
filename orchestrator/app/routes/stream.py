"""Websocket stream routes."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

router = APIRouter(tags=["stream"])


@router.websocket("/ws/sessions/{session_id}/stream")
async def stream_session(session_id: str, websocket: WebSocket) -> None:
    await websocket.app.state.relay.subscribe(session_id, websocket)
