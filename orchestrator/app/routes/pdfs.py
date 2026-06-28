"""Safe local-PDF serving for the Research tab.

Serves PDFs **only** from the approved directories in `Settings.pdf_root_paths` (default: the curated
knowledge/data tree). Arbitrary filesystem paths are rejected — the requested path is resolved and must
live inside an approved root, and must be a .pdf file. This is the local-PDF counterpart to arXiv's
direct pdf_url; it never fetches from the network.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])


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
