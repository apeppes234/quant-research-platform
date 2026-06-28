"""Ingest SSRN papers -> corpus 'papers'. See ../README.md + docs/06.

SSRN has variable access controls, so this job consumes a curator-provided JSONL manifest instead of
scraping blindly. Each line should include title, abstract or text, url, and optional tags.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .common import KnowledgeChunk, chunk_text, upsert_chunks


def load_manifest(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_chunks(rows: list[dict]) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for row in rows:
        title = str(row.get("title") or "Untitled SSRN paper")
        body = str(row.get("text") or row.get("abstract") or "")
        url = str(row.get("url") or row.get("source") or "ssrn")
        citation = str(row.get("citation") or f"{title}, SSRN")
        tags = ["ssrn", *[str(tag) for tag in row.get("tags", [])]]
        chunks.extend(
            chunk_text(
                f"# {title}\n\n{body}",
                corpus="papers",
                source=url,
                citation=citation,
                tags=tags,
                metadata={"provider": "ssrn"},
            )
        )
    return chunks


def ingest(*, manifest: str | None = None, limit: int | None = None, upsert: bool = True) -> int:
    manifest_value = manifest or os.getenv("SSRN_PAPERS_JSONL", "")
    if not manifest_value:
        return 0
    manifest_path = Path(manifest_value)
    if not manifest_path.is_file():
        return 0
    rows = load_manifest(manifest_path)
    if limit:
        rows = rows[:limit]
    chunks = build_chunks(rows)
    return upsert_chunks(chunks) if upsert else len(chunks)
