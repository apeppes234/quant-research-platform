"""FastAPI app factory for the orchestrator (data plane).

Mounts the session/stream/steering routes and starts the websocket relay. The actual Managed Agents
SSE consumption happens per-session in events/sse_consumer.py.

STATUS: scaffold. See docs/10-orchestrator.md for the design and the three must-be-right patterns.

    uv run uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI

# from .routes import sessions, stream, steering


def create_app() -> FastAPI:
    app = FastAPI(title="Quant Research Orchestrator")

    # app.include_router(sessions.router)   # POST /sessions, /message, /define_outcome
    # app.include_router(stream.router)     # WS  /sessions/{id}/stream
    # app.include_router(steering.router)   # POST /interrupt, /confirm

    @app.get("/health")
    def health():
        return {"status": "scaffold"}

    return app


app = create_app()
