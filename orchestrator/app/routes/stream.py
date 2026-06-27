"""Websocket route: WS /sessions/{id}/stream.

On connect, subscribe the socket to the relay for this session. A background task runs
events.sse_consumer.consume(session_id) and publishes normalized events to all subscribers via ws_relay.
Each event carries its `id` for client-side dedupe.

STATUS: scaffold.
"""
from fastapi import APIRouter

router = APIRouter(tags=["stream"])

# @router.websocket("/sessions/{session_id}/stream")
# async def stream(ws: WebSocket, session_id: str): ...
