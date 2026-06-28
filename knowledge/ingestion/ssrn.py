"""Ingest curated SSRN quant-research papers -> corpus 'papers'. See ../README.md + docs/06.

SSRN is **not** market data and is **not** scraped. Access controls on SSRN vary per paper, so this
job consumes a curator-provided JSONL manifest and ingests *only* the papers explicitly listed there.
Each manifest row describes one paper (title, abstract/text, url, citation, and rich quant metadata) so
the Paper Agent can use the result as idea/citation grounding — not as a price/return data source.

Manifest fields (all optional unless noted under "Validation"):

    title           paper title (used for the chunk header and citation fallback)
    authors         list[str] or string of author names
    year            publication/working-paper year
    abstract        paper abstract (ingested when `text` is absent)
    text            full/long-form text to chunk (preferred over abstract when present)
    url             SSRN abstract URL (or any canonical source URL)
    source          alias for url; either satisfies the source requirement
    citation        human-readable citation; defaults to "<title> (<year>), SSRN"
    tags            list[str] of free-form tags; "ssrn" is always added
    ssrn_id         SSRN abstract id
    doi             DOI if assigned
    license         license / usage terms string
    rights_checked  bool — curator confirmed redistribution rights for the ingested text
    strategy_family momentum | stat-arb | factor | volatility | validation | ...
    asset_class     equities | futures | fx | options | crypto | multi-asset | ...
    signal_type     cross-sectional | time-series | event | microstructure | ...
    data_needed     list[str] or string describing data required to test the idea
    notes           curator notes / hypothesis framing for the Paper Agent
    local_pdf_path  path to a LOCAL pdf; text is extracted only when `text` is empty (never downloaded)

Validation: a row is skipped (with a warning, without crashing the job) when it lacks a title, lacks a
url/source, or lacks any body content (abstract, text, or a readable local_pdf_path).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .common import KnowledgeChunk, chunk_text, dedupe_chunks, upsert_chunks

# Metadata keys copied verbatim from the manifest row into chunk metadata when present.
_METADATA_KEYS = (
    "authors",
    "year",
    "ssrn_id",
    "doi",
    "license",
    "rights_checked",
    "strategy_family",
    "asset_class",
    "signal_type",
    "data_needed",
    "notes",
)

# Single-valued classification fields that also become tags so the Paper Agent can filter cheaply
# via the GIN tag index (in addition to the metadata copy).
_TAG_FROM_METADATA = ("strategy_family", "asset_class", "signal_type")


def load_manifest(path: Path) -> list[dict]:
    """Read a JSONL manifest into a list of rows. Blank lines are ignored."""

    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                _warn(f"manifest line {line_no} is not valid JSON ({exc}); skipping")
    return rows


def extract_pdf_text(path: Path) -> str:
    """Extract text from a LOCAL pdf. Returns "" if the file or a pdf parser is unavailable.

    Uses pypdf when installed, falling back to PyMuPDF (fitz). This only ever reads a local file —
    it never downloads a PDF from SSRN.
    """

    if not path.is_file():
        _warn(f"local_pdf_path does not exist: {path}")
        return ""

    try:  # preferred: pypdf (lightweight, pure-python)
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages).strip()
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover - corrupt/encrypted pdf
        _warn(f"pypdf failed to read {path} ({exc})")
        return ""

    try:  # fallback: PyMuPDF
        import fitz

        with fitz.open(str(path)) as doc:
            pages = [page.get_text() for page in doc]
        return "\n\n".join(pages).strip()
    except ImportError:
        _warn(
            f"cannot extract {path}: install 'pypdf' (or 'pymupdf') to ingest local PDFs"
        )
        return ""
    except Exception as exc:  # pragma: no cover - corrupt/encrypted pdf
        _warn(f"PyMuPDF failed to read {path} ({exc})")
        return ""


def _resolve_body(row: dict, *, manifest_dir: Path | None) -> str:
    """Pick the text to chunk: explicit text > abstract > extracted local PDF."""

    text = str(row.get("text") or "").strip()
    if text:
        return text
    abstract = str(row.get("abstract") or "").strip()
    if abstract:
        return abstract
    pdf_path = row.get("local_pdf_path")
    if pdf_path:
        path = Path(str(pdf_path))
        if not path.is_absolute() and manifest_dir is not None:
            path = manifest_dir / path
        return extract_pdf_text(path)
    return ""


def _validate(row: dict) -> str | None:
    """Return a human-readable reason the row is invalid, or None when it is ingestible."""

    if not str(row.get("title") or "").strip():
        return "missing title"
    if not str(row.get("url") or row.get("source") or "").strip():
        return "missing url/source"
    has_body = bool(
        str(row.get("text") or "").strip()
        or str(row.get("abstract") or "").strip()
        or str(row.get("local_pdf_path") or "").strip()
    )
    if not has_body:
        return "missing abstract/text/local_pdf_path"
    return None


def _row_metadata(row: dict) -> dict[str, object]:
    metadata: dict[str, object] = {"provider": "ssrn"}
    for key in _METADATA_KEYS:
        value = row.get(key)
        if value not in (None, "", []):
            metadata[key] = value
    return metadata


def _row_tags(row: dict) -> list[str]:
    tags = ["ssrn"]
    for tag in row.get("tags", []) or []:
        tag = str(tag).strip()
        if tag and tag not in tags:
            tags.append(tag)
    for key in _TAG_FROM_METADATA:
        value = row.get(key)
        if isinstance(value, str) and value.strip() and value.strip() not in tags:
            tags.append(value.strip())
    return tags


def build_chunks(rows: list[dict], *, manifest_dir: Path | None = None) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for row in rows:
        reason = _validate(row)
        if reason:
            _warn(f"skipping row ({reason}): {row.get('title') or row.get('url') or row!r}")
            continue

        body = _resolve_body(row, manifest_dir=manifest_dir)
        if not body:
            _warn(f"skipping row (no extractable text): {row.get('title')}")
            continue

        title = str(row["title"]).strip()
        url = str(row.get("url") or row.get("source")).strip()
        year = row.get("year")
        citation = str(row.get("citation") or f"{title}{f' ({year})' if year else ''}, SSRN").strip()

        chunks.extend(
            chunk_text(
                f"# {title}\n\n{body}",
                corpus="papers",
                source=url,
                citation=citation,
                tags=_row_tags(row),
                metadata=_row_metadata(row),
            )
        )
    return dedupe_chunks(chunks)


def ingest(*, manifest: str | None = None, limit: int | None = None, upsert: bool = True) -> int:
    manifest_value = manifest or os.getenv("SSRN_PAPERS_JSONL", "")
    if not manifest_value:
        _warn("no manifest configured (set SSRN_PAPERS_JSONL or pass manifest=...); nothing to ingest")
        return 0
    manifest_path = Path(manifest_value)
    if not manifest_path.is_file():
        _warn(f"manifest not found: {manifest_path}; nothing to ingest")
        return 0
    rows = load_manifest(manifest_path)
    if limit:
        rows = rows[:limit]
    chunks = build_chunks(rows, manifest_dir=manifest_path.resolve().parent)
    return upsert_chunks(chunks) if upsert else len(chunks)


def _warn(message: str) -> None:
    print(f"[ssrn] WARNING: {message}", file=sys.stderr)
