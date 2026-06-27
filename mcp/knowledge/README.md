# mcp/knowledge — the `search_knowledge` MCP server

Exposes a single semantic-search tool over the self-hosted vector DB (pgvector/Qdrant) that the Paper,
Feature, and Modeling agents use to ground designs (docs/06).

## Tool

```
search_knowledge(query: str, corpus?: "papers"|"repo"|"strategy_library"|"contract",
                 tags?: list[str], k?: int = 8)
  -> [{ text, source, citation, corpus, score, metadata }]
```

Always return a **citation** (powers the provenance view, docs/09).

## Run

```bash
MCP_TRANSPORT=streamable-http uv run src/server.py      # or: make mcp-knowledge
```

Reads `VECTORDB_KIND` + DB connection from env. The corpora are populated by the ingestion jobs in
[`knowledge/`](../../knowledge/).

## Files

```
src/server.py   # FastMCP server; registers search_knowledge; transport from MCP_TRANSPORT
src/search.py   # embedding + vector query against pgvector/Qdrant
```

STATUS: scaffold.
