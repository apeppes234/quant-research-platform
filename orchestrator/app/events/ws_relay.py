"""Fan-out normalized events to connected browser websockets.

Holds the set of connected clients per session and pushes each normalized event (from sse_consumer +
schema.normalize) with its `id` so the frontend (frontend/src/api/ws.ts) can dedupe. The frontend may
reconnect; on reconnect it re-subscribes and the orchestrator may replay recent buffered events — dedupe
by id on the client.

STATUS: scaffold.
"""


class WsRelay:
    def __init__(self) -> None:
        self._clients: dict[str, set] = {}   # session_id -> set[WebSocket]

    async def subscribe(self, session_id: str, ws) -> None: ...
    async def unsubscribe(self, session_id: str, ws) -> None: ...
    async def publish(self, session_id: str, normalized_event: dict) -> None: ...
