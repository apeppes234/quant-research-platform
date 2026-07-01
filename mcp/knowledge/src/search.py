"""search_knowledge implementation over pgvector, with a citation-bearing local fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from knowledge.ingestion.common import (
        EMBEDDING_DIM,
        FROZEN_EMBEDDING_MODEL,
        default_pg_dsn,
        embed_text,
        vector_literal,
    )
except ImportError:  # pragma: no cover - local MCP image fallback
    EMBEDDING_DIM = int(os.getenv("KNOWLEDGE_EMBEDDING_DIM", "384"))
    FROZEN_EMBEDDING_MODEL = os.getenv("KNOWLEDGE_EMBEDDING_MODEL", "intfloat/e5-small-v2")

    def default_pg_dsn() -> str:
        return os.getenv("VECTORDB_DSN", "")

    def embed_text(text: str) -> list[float]:
        return [0.0] * EMBEDDING_DIM

    def vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(str(value) for value in vector) + "]"


# Snippet caps keep search_knowledge payloads bounded. Un-capped, a single retrieval could
# dump whole files (the contract fallback) or 8+ full chunks into every agent turn — the biggest
# per-query token sink. Contract chunks get more room (agents author against them); everything
# else is snippet-sized. Tunable via env without a redeploy of callers.
_SNIPPET_CHARS = int(os.getenv("KNOWLEDGE_SNIPPET_CHARS", "1600"))
_CONTRACT_SNIPPET_CHARS = int(os.getenv("KNOWLEDGE_CONTRACT_SNIPPET_CHARS", "4000"))
_MAX_K = int(os.getenv("KNOWLEDGE_MAX_K", "12"))


def _snippet(text: str, corpus: str | None) -> tuple[str, int | None]:
    """Bound a chunk to a readable snippet. Returns (snippet, full_length_if_truncated)."""
    text = text or ""
    cap = _CONTRACT_SNIPPET_CHARS if corpus == "contract" else _SNIPPET_CHARS
    if len(text) <= cap:
        return text, None
    # Prefer a line break, then a word break, so we don't sever mid-token.
    cut = text.rfind("\n", 0, cap)
    if cut < cap // 2:
        cut = text.rfind(" ", 0, cap)
    if cut < cap // 2:
        cut = cap
    return text[:cut].rstrip() + "\n…[truncated]", len(text)


def _bound_chunk(row: dict) -> dict:
    """Apply the snippet cap to one result row, recording truncation in metadata."""
    snippet, full_length = _snippet(str(row.get("text", "")), row.get("corpus"))
    if full_length is None:
        return row
    metadata = {**(row.get("metadata") or {}), "truncated": True, "full_length": full_length}
    return {**row, "text": snippet, "metadata": metadata}


REPO_ROOT = next(
    (
        candidate
        for candidate in [Path.cwd(), *Path(__file__).resolve().parents]
        if (candidate / "contract" / "contract.json").exists()
    ),
    Path(__file__).resolve().parents[1],
)
CONTRACT_FILES = [
    ("contract/strategy_authoring_contract.md", "contract", ["contract", "rubric"]),
    ("contract/contract.json", "contract", ["contract", "machine-readable"]),
    ("contract/templates/starter_algorithm.py", "contract", ["contract", "starter"]),
    ("contract/validator/validate.py", "contract", ["contract", "validator"]),
    ("docs/04-quantconnect.md", "contract", ["quantconnect", "mcp"]),
    ("docs/07-iteration-rubric.md", "contract", ["rubric", "iteration"]),
    ("docs/08-antibias-guardrails.md", "contract", ["bias", "ledger"]),
    ("docs/11-authoring-contract.md", "contract", ["contract", "validator"]),
]


async def search(
    query: str,
    corpus: str | None = None,
    tags: list[str] | None = None,
    k: int = 8,
) -> list[dict]:
    if not query.strip():
        return []

    limit = max(1, min(k, _MAX_K))
    if os.getenv("VECTORDB_KIND", "pgvector") == "pgvector" and _has_vector_db_config():
        try:
            rows = _search_pgvector(query, corpus=corpus, tags=tags or [], limit=limit)
            if rows:
                return [_bound_chunk(row) for row in rows]
        except Exception as exc:  # pragma: no cover - depends on external DB
            if os.getenv("KNOWLEDGE_STRICT_VECTORDB", "").lower() == "true":
                raise
            return [_fallback_error(query, corpus, tags, exc)]

    return [_bound_chunk(row) for row in _search_fallback(query, corpus=corpus, tags=tags or [], limit=limit)]


def _search_pgvector(query: str, *, corpus: str | None, tags: list[str], limit: int) -> list[dict]:
    import psycopg

    vector = vector_literal(embed_text(f"query: {query}"))
    where: list[str] = []
    params: list[Any] = [vector]
    if corpus:
        where.append("corpus = %s")
        params.append(corpus)
    if tags:
        where.append("tags && %s")
        params.append(tags)
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    params.append(limit)

    with psycopg.connect(default_pg_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT corpus, source, citation, tags, chunk_text,
                       1 - (embedding <=> %s::vector) AS score,
                       metadata
                  FROM knowledge_chunks
                  {where_sql}
              ORDER BY embedding <=> %s::vector
                 LIMIT %s
                """,
                [vector, *params[1:-1], vector, limit],
            )
            rows = cur.fetchall()

    return [
        {
            "text": row[4],
            "source": row[1],
            "citation": row[2],
            "corpus": row[0],
            "score": float(row[5] or 0.0),
            "metadata": {
                **(row[6] or {}),
                "tags": row[3] or [],
                "embedding_model": FROZEN_EMBEDDING_MODEL,
            },
        }
        for row in rows
    ]


def _search_fallback(query: str, *, corpus: str | None, tags: list[str], limit: int) -> list[dict]:
    documents = _fallback_documents()
    if corpus:
        documents = [doc for doc in documents if doc["corpus"] == corpus]
    if tags:
        wanted = set(tags)
        documents = [doc for doc in documents if wanted.intersection(doc.get("tags", []))]

    query_terms = set(query.lower().split())
    scored = []
    for doc in documents:
        text = str(doc["text"])
        haystack = f"{doc['citation']} {text}".lower()
        lexical = sum(1 for term in query_terms if term in haystack)
        contract_boost = 2 if doc["corpus"] == "contract" and ("contract" in query_terms or "rubric" in query_terms) else 0
        score = float(lexical + contract_boost) / max(1.0, len(query_terms))
        if score > 0 or not scored:
            scored.append({**doc, "score": score})

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit] or [_phase4_empty(query, corpus, tags)]


def _fallback_documents() -> list[dict]:
    docs: list[dict] = []
    for path, corpus, tags in CONTRACT_FILES:
        file_path = REPO_ROOT / path
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8")
        else:
            text = f"{path} is expected in the contract corpus but is not bundled in this MCP image."
        docs.append(
            {
                "text": text,
                "source": "quant-research-platform",
                "citation": path,
                "corpus": corpus,
                "tags": tags,
                "metadata": {
                    "fallback": True,
                    "embedding_model": FROZEN_EMBEDDING_MODEL,
                    "embedding_dim": EMBEDDING_DIM,
                },
            }
        )

    jsonl_dir = os.getenv("KNOWLEDGE_LOCAL_JSONL_DIR")
    if jsonl_dir:
        for path in Path(jsonl_dir).glob("*.jsonl"):
            docs.extend(_jsonl_documents(path))
    return docs


def _jsonl_documents(path: Path) -> list[dict]:
    docs: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            docs.append(
                {
                    "text": row.get("text", ""),
                    "source": row.get("source", str(path)),
                    "citation": row.get("citation", str(path)),
                    "corpus": row.get("corpus", path.stem),
                    "tags": row.get("tags", []),
                    "metadata": {**row.get("metadata", {}), "fallback_jsonl": str(path)},
                }
            )
    return docs


def _has_vector_db_config() -> bool:
    return bool(
        os.getenv("VECTORDB_DSN")
        or os.getenv("DATABASE_URL")
        or (os.getenv("POSTGRES_HOST") and os.getenv("POSTGRES_DB"))
    )


def _fallback_error(query: str, corpus: str | None, tags: list[str] | None, exc: Exception) -> dict:
    return {
        "text": "Vector search failed; returning contract fallback. Check pgvector connectivity.",
        "source": "mcp/knowledge",
        "citation": "mcp/knowledge/src/search.py",
        "corpus": corpus or "contract",
        "score": 0.0,
        "metadata": {"query": query, "tags": tags or [], "error": str(exc), "fallback": True},
    }


def _phase4_empty(query: str, corpus: str | None, tags: list[str]) -> dict:
    return {
        "text": "No knowledge chunks matched. Run knowledge ingestion or query corpus='contract'.",
        "source": "mcp/knowledge",
        "citation": "docs/06-knowledge-layer.md",
        "corpus": corpus or "unknown",
        "score": 0.0,
        "metadata": {"query": query, "tags": tags, "fallback": True},
    }
