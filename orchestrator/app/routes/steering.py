"""Steering routes for interrupts and gated tool confirmations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/sessions", tags=["steering"])


class InterruptRequest(BaseModel):
    reason: str | None = None


class ConfirmToolRequest(BaseModel):
    tool_use_id: str = Field(min_length=1)
    result: str = Field(pattern="^(allow|deny)$")
    session_thread_id: str | None = None


@router.post("/{session_id}/interrupt")
async def interrupt(session_id: str, request: Request, body: InterruptRequest | None = None) -> dict:
    try:
        await request.app.state.session_manager.interrupt(
            session_id,
            reason=body.reason if body else None,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{session_id}/confirm")
async def confirm_tool(session_id: str, request: Request, body: ConfirmToolRequest) -> dict:
    try:
        await request.app.state.session_manager.confirm_tool(
            session_id,
            tool_use_id=body.tool_use_id,
            result=body.result,
            session_thread_id=body.session_thread_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True}
