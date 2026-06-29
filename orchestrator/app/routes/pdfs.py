"""Safe local-PDF serving for the Research tab.

Serves PDFs **only** from the approved directories in `Settings.pdf_root_paths` (default: the curated
knowledge/data tree). Arbitrary filesystem paths are rejected — the requested path is resolved and must
live inside an approved root, and must be a .pdf file. This is the local-PDF counterpart to arXiv's
direct pdf_url; it never fetches from the network.
"""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote, urlparse, urlunparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])

_ARXIV_ID_RE = re.compile(r"^[A-Za-z0-9._/-]+(?:\.pdf)?$")
_ARXIV_HOSTS = {"arxiv.org", "www.arxiv.org"}


@router.get("/arxiv")
async def serve_arxiv_pdf(url: str) -> Response:
    """Proxy an arXiv PDF as same-origin content so browsers can embed it reliably."""

    try:
        pdf_url = _normalize_arxiv_pdf_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await _fetch_arxiv_pdf(pdf_url)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{_arxiv_filename(pdf_url)}"',
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.get("")
def serve_pdf(path: str, request: Request) -> FileResponse:
    roots: list[Path] = request.app.state.settings.pdf_root_paths
    if not roots:
        raise HTTPException(status_code=404, detail="No approved PDF directories are configured")

    try:
        candidate = Path(path).expanduser().resolve()
    except (OSError, RuntimeError) as exc:  # pragma: no cover - exotic path inputs
        raise HTTPException(status_code=400, detail="Invalid path") from exc

    if candidate.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only .pdf files may be served")

    if not _within_approved_root(candidate, roots):
        # Do not leak whether the file exists outside the sandbox.
        raise HTTPException(status_code=403, detail="Path is outside the approved PDF directories")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        candidate,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{candidate.name}"'},
    )


def _within_approved_root(candidate: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            candidate.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _normalize_arxiv_pdf_url(raw_url: str) -> str:
    value = raw_url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only arXiv HTTP(S) URLs may be proxied")
    if parsed.netloc.lower() not in _ARXIV_HOSTS:
        raise ValueError("Only arXiv PDFs may be proxied")

    path = parsed.path
    if path.startswith("/abs/"):
        paper_id = path.removeprefix("/abs/")
    elif path.startswith("/pdf/"):
        paper_id = path.removeprefix("/pdf/")
    else:
        raise ValueError("Only arXiv /abs/ or /pdf/ URLs may be proxied")

    paper_id = unquote(paper_id).strip("/")
    if not paper_id or ".." in paper_id or "\\" in paper_id or not _ARXIV_ID_RE.fullmatch(paper_id):
        raise ValueError("Invalid arXiv paper id")
    if paper_id.endswith(".pdf"):
        paper_id = paper_id.removesuffix(".pdf")

    return urlunparse(("https", "arxiv.org", f"/pdf/{paper_id}", "", "", ""))


async def _fetch_arxiv_pdf(pdf_url: str) -> bytes:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30,
            headers={"User-Agent": "quant-research-platform/0.1"},
        ) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(status_code=status_code, detail="arXiv PDF could not be fetched") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="arXiv PDF could not be fetched") from exc

    content_type = response.headers.get("content-type", "")
    if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
        raise HTTPException(status_code=502, detail="arXiv did not return a PDF")
    return response.content


def _arxiv_filename(pdf_url: str) -> str:
    paper_id = urlparse(pdf_url).path.removeprefix("/pdf/").strip("/") or "paper"
    return f"arxiv-{paper_id.replace('/', '-')}.pdf"
