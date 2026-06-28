"""Session creation and user-event routes."""

from __future__ import annotations

import json
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..rubric import default_rubric_markdown
from ..sessions.manager import SessionManager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class OutcomeKickoff(BaseModel):
    description: str = Field(min_length=1)
    rubric: str | None = None
    max_iterations: int = Field(default=5, ge=1, le=20)


class CreateSessionRequest(BaseModel):
    message: str | None = Field(default=None, min_length=1)
    outcome: OutcomeKickoff | None = None


class MessageRequest(BaseModel):
    content: str = Field(min_length=1)


class DefineOutcomeRequest(BaseModel):
    description: str = Field(min_length=1)
    rubric: str | None = None
    max_iterations: int = Field(default=5, ge=1, le=20)


@router.post("")
async def create_session(request: Request, body: CreateSessionRequest | None = None) -> dict:
    manager = _manager(request)
    try:
        session_id = await manager.create_session()
        if body and body.outcome:
            await manager.define_outcome(
                session_id,
                description=body.outcome.description,
                rubric=body.outcome.rubric or default_rubric_markdown(),
                max_iterations=body.outcome.max_iterations,
            )
        elif body and body.message:
            await manager.send_user_message(session_id, body.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"sessionId": session_id}


@router.post("/{session_id}/message")
async def send_message(session_id: str, request: Request, body: MessageRequest) -> dict:
    try:
        await _manager(request).send_user_message(session_id, body.content)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{session_id}/define_outcome")
async def define_outcome(session_id: str, request: Request, body: DefineOutcomeRequest) -> dict:
    try:
        await _manager(request).define_outcome(
            session_id,
            description=body.description,
            rubric=body.rubric or default_rubric_markdown(),
            max_iterations=body.max_iterations,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/{session_id}/results")
async def get_results(session_id: str, request: Request) -> dict:
    try:
        results = await _manager(request).latest_results(session_id)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"results.json is not valid JSON: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if results is None:
        raise HTTPException(status_code=404, detail="results.json is not available for this session yet")
    return {"results": results}


@router.get("/{session_id}/files")
async def list_files(session_id: str, request: Request) -> dict:
    try:
        files = await _manager(request).output_files(session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"files": [_with_download_url(session_id, file) for file in files]}


@router.get("/{session_id}/report")
async def get_report(session_id: str, request: Request) -> dict:
    try:
        report = await _manager(request).latest_report(session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if report is None:
        raise HTTPException(status_code=404, detail="report.pdf is not available for this session yet")
    return {"file": _with_download_url(session_id, report)}


@router.get("/{session_id}/files/{file_id}/download")
async def download_file(session_id: str, file_id: str, request: Request) -> Response:
    try:
        metadata, content = await _manager(request).download_output_file(session_id, file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File is not available for this session") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    filename = str(metadata.get("filename") or f"{file_id}.bin")
    safe_filename = filename.replace("\n", " ").replace("\r", " ")
    media_type = str(metadata.get("mimeType") or "application/octet-stream")
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{quote(safe_filename)}"
            )
        },
    )


@router.get("/rubric/default")
async def get_default_rubric() -> dict:
    return {"rubric": default_rubric_markdown()}


def _manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


def _with_download_url(session_id: str, file: dict) -> dict:
    return {
        **file,
        "downloadUrl": f"/api/sessions/{session_id}/files/{file['id']}/download",
    }
