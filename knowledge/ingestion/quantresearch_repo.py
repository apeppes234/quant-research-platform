"""Ingest letianzj/QuantResearch notebooks -> corpus 'repo' (cell-level chunks). docs/06."""

from __future__ import annotations

import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .common import KnowledgeChunk, notebook_cell_chunks, upsert_chunks

ARCHIVE_URL = "https://github.com/letianzj/QuantResearch/archive/refs/heads/master.zip"


def source_root(path: str | None = None) -> Path:
    configured = Path(path or os.getenv("QUANTRESEARCH_REPO_PATH", ""))
    if configured.exists():
        return configured
    temp_dir = Path(tempfile.mkdtemp(prefix="quantresearch_repo_"))
    archive_path = temp_dir / "repo.zip"
    urllib.request.urlretrieve(ARCHIVE_URL, archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(temp_dir)
    matches = list(temp_dir.glob("QuantResearch-*"))
    if not matches:
        raise RuntimeError("Downloaded QuantResearch archive did not contain the expected root")
    return matches[0]


def build_chunks(root: Path, *, limit: int | None = None) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for notebook in sorted(root.rglob("*.ipynb")):
        tags = _tags_for_path(notebook)
        chunks.extend(notebook_cell_chunks(notebook, corpus="repo", tags=tags))
        if limit and len(chunks) >= limit:
            return chunks[:limit]
    return chunks


def ingest(*, path: str | None = None, limit: int | None = None, upsert: bool = True) -> int:
    chunks = build_chunks(source_root(path), limit=limit)
    return upsert_chunks(chunks) if upsert else len(chunks)


def _tags_for_path(path: Path) -> list[str]:
    lower = str(path).lower()
    tags = ["quantresearch"]
    for key in ("kalman", "pairs", "cointegration", "momentum", "mean", "garch", "arima", "hmm", "fama", "var"):
        if key in lower:
            tags.append("mean-reversion" if key == "mean" else key)
    return tags
