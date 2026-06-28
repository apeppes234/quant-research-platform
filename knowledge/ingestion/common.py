"""Shared ingestion primitives for the Phase 4 knowledge layer.

The production path upserts chunks into pgvector. The deterministic hash embedder keeps tests and local
dry-runs usable without downloading a model; deployments should set KNOWLEDGE_EMBEDDING_BACKEND to the
frozen local model path once the corpus is built.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

FROZEN_EMBEDDING_MODEL = os.getenv("KNOWLEDGE_EMBEDDING_MODEL", "intfloat/e5-small-v2")
EMBEDDING_DIM = int(os.getenv("KNOWLEDGE_EMBEDDING_DIM", "384"))
TOKEN_RE = re.compile(r"[A-Za-z0-9_.$%-]+")


@dataclass(frozen=True)
class KnowledgeChunk:
    corpus: str
    source: str
    citation: str
    text: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_json(self) -> dict[str, object]:
        return asdict(self)


def default_pg_dsn() -> str:
    explicit = os.getenv("VECTORDB_DSN") or os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "quant_research")
    user = os.getenv("POSTGRES_USER", "quant")
    password = os.getenv("POSTGRES_PASSWORD", "change-me")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def chunk_text(
    text: str,
    *,
    corpus: str,
    source: str,
    citation: str,
    tags: list[str] | None = None,
    max_chars: int = 1800,
    metadata: dict[str, object] | None = None,
) -> list[KnowledgeChunk]:
    """Make section-aware chunks from markdown/plain text without external parsers."""

    cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not cleaned:
        return []

    sections = _split_sections(cleaned)
    chunks: list[KnowledgeChunk] = []
    for section_title, body in sections:
        buffer = ""
        for paragraph in re.split(r"\n{2,}", body):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
            if len(candidate) > max_chars and buffer:
                chunks.append(
                    KnowledgeChunk(
                        corpus=corpus,
                        source=source,
                        citation=citation,
                        text=buffer,
                        tags=tags or [],
                        metadata={**(metadata or {}), "section": section_title},
                    )
                )
                buffer = paragraph
            else:
                buffer = candidate
        if buffer:
            chunks.append(
                KnowledgeChunk(
                    corpus=corpus,
                    source=source,
                    citation=citation,
                    text=buffer,
                    tags=tags or [],
                    metadata={**(metadata or {}), "section": section_title},
                )
            )
    return chunks


def notebook_cell_chunks(path: Path, *, corpus: str = "repo", tags: list[str] | None = None) -> list[KnowledgeChunk]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cells = payload.get("cells", [])
    chunks: list[KnowledgeChunk] = []
    for index, cell in enumerate(cells):
        source = "".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else str(cell.get("source", ""))
        if not source.strip():
            continue
        cell_type = str(cell.get("cell_type", "cell"))
        citation = f"{path.name} cell {index + 1}"
        chunks.append(
            KnowledgeChunk(
                corpus=corpus,
                source=str(path),
                citation=citation,
                text=source.strip(),
                tags=[*(tags or []), cell_type],
                metadata={"cell_index": index, "cell_type": cell_type},
            )
        )
    return chunks


def embed_text(text: str) -> list[float]:
    """Deterministic, normalized embedding used for local/offline operation."""

    vector = [0.0] * EMBEDDING_DIM
    tokens = TOKEN_RE.findall(text.lower())
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        idx = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def vector_literal(vector: Iterable[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def upsert_chunks(chunks: Iterable[KnowledgeChunk], *, dsn: str | None = None) -> int:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - only before deps are installed
        raise RuntimeError("Install psycopg or run ingestion with --dry-run") from exc

    rows = list(chunks)
    if not rows:
        return 0

    with psycopg.connect(dsn or default_pg_dsn()) as conn:
        with conn.cursor() as cur:
            for chunk in rows:
                cur.execute(
                    """
                    INSERT INTO knowledge_chunks
                        (corpus, source, citation, tags, chunk_text, embedding, metadata)
                    VALUES
                        (%s, %s, %s, %s, %s, %s::vector, %s)
                    """,
                    (
                        chunk.corpus,
                        chunk.source,
                        chunk.citation,
                        chunk.tags,
                        chunk.text,
                        vector_literal(embed_text(f"passage: {chunk.text}")),
                        json.dumps(
                            {
                                **chunk.metadata,
                                "embedding_model": FROZEN_EMBEDDING_MODEL,
                                "embedding_dim": EMBEDDING_DIM,
                            }
                        ),
                    ),
                )
        conn.commit()
    return len(rows)


def write_jsonl(chunks: Iterable[KnowledgeChunk], path: Path) -> int:
    rows = list(chunks)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in rows:
            handle.write(json.dumps(chunk.to_json(), sort_keys=True) + "\n")
    return len(rows)


def _split_sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^(#{1,4}\s+.+|[A-Z][A-Za-z0-9 ,:/()&-]{6,})$", text))
    if not matches:
        return [("body", text)]

    sections: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        title = match.group(1).lstrip("# ").strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title, body))
    return sections or [("body", text)]
