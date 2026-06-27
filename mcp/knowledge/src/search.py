"""Embedding + vector query for search_knowledge. STATUS: scaffold.

Embed the query with the SAME model used at ingestion (docs/14 O2 — freeze the choice), then query
pgvector/Qdrant filtered by corpus/tags, returning {text, source, citation, corpus, score, metadata}.
Schema: knowledge/schema/vectordb_schema.sql.
"""


async def search(query: str, corpus: str | None = None,
                 tags: list[str] | None = None, k: int = 8) -> list[dict]:
    raise NotImplementedError("scaffold — embed query + vector search; see docs/06")
