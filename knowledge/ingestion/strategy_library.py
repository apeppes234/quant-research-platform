"""Ingest QuantConnect Tutorials/04 Strategy Library -> corpus 'strategy_library'. docs/06."""

from __future__ import annotations

import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .common import KnowledgeChunk, chunk_text, upsert_chunks

ARCHIVE_URL = "https://github.com/QuantConnect/Tutorials/archive/refs/heads/master.zip"


def source_root(path: str | None = None) -> Path:
    configured = Path(path or os.getenv("QC_STRATEGY_LIBRARY_PATH", ""))
    if configured.exists():
        return configured
    if os.getenv("ALLOW_QC_STRATEGY_LIBRARY_INGEST", "").lower() != "true":
        raise RuntimeError(
            "Set QC_STRATEGY_LIBRARY_PATH or ALLOW_QC_STRATEGY_LIBRARY_INGEST=true after confirming licensing."
        )
    temp_dir = Path(tempfile.mkdtemp(prefix="qc_strategy_library_"))
    archive_path = temp_dir / "tutorials.zip"
    urllib.request.urlretrieve(ARCHIVE_URL, archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(temp_dir)
    matches = list(temp_dir.glob("Tutorials-*/04 Strategy Library"))
    if not matches:
        raise RuntimeError("Downloaded QC Tutorials archive did not contain 04 Strategy Library")
    return matches[0]


def build_chunks(root: Path, *, limit: int | None = None) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".md", ".py", ".ipynb", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        citation = f"QuantConnect Strategy Library: {path.relative_to(root)}"
        chunks.extend(
            chunk_text(
                text,
                corpus="strategy_library",
                source=str(path),
                citation=citation,
                tags=["quantconnect", "strategy-library", *_tags_for_path(path)],
                metadata={"provider": "quantconnect"},
            )
        )
        if limit and len(chunks) >= limit:
            return chunks[:limit]
    return chunks


def ingest(*, path: str | None = None, limit: int | None = None, upsert: bool = True) -> int:
    chunks = build_chunks(source_root(path), limit=limit)
    return upsert_chunks(chunks) if upsert else len(chunks)


def _tags_for_path(path: Path) -> list[str]:
    lower = str(path).lower()
    tags = []
    for key in ("momentum", "mean", "pairs", "options", "fundamental", "regime", "etf", "factor"):
        if key in lower:
            tags.append("mean-reversion" if key == "mean" else key)
    return tags
