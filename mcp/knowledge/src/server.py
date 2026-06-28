"""search_knowledge MCP server (FastMCP, streamable-http capable)."""

import os

from mcp.server.fastmcp import FastMCP

try:
    from .search import search
except ImportError:  # Allows `uv run src/server.py`.
    from search import search

transport = os.getenv("MCP_TRANSPORT", "stdio")
port = int(os.getenv("MCP_PORT", "9000"))

mcp = FastMCP("search_knowledge", host="0.0.0.0", port=port)


@mcp.tool()
async def search_knowledge(
    query: str,
    filters: dict | None = None,
    corpus: str | None = None,
    tags: list[str] | None = None,
    k: int = 8,
) -> list[dict]:
    """Search quant research knowledge and return citation-bearing snippets."""
    if filters:
        corpus = corpus or filters.get("corpus")
        tags = tags or filters.get("tags")
    return await search(query, corpus=corpus, tags=tags, k=k)


if __name__ == "__main__":
    mcp.run(transport=transport)
