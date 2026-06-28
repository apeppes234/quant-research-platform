"""FastAPI app factory for the Phase 1 orchestrator."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .clients.anthropic_client import ManagedAgentsClient
from .config import get_settings
from .events.ws_relay import SessionRelay
from .routes import pdfs, sessions, steering, stream
from .sessions.manager import SessionManager


def create_app() -> FastAPI:
    settings = get_settings()
    relay = SessionRelay()

    app = FastAPI(title="Quant Research Orchestrator")
    app.state.settings = settings
    app.state.relay = relay
    app.state.session_manager = SessionManager(
        settings=settings,
        client=ManagedAgentsClient(settings),
        relay=relay,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions.router)
    app.include_router(stream.router)
    app.include_router(steering.router)
    app.include_router(pdfs.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
