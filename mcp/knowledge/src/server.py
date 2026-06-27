"""search_knowledge MCP server (FastMCP, streamable-http capable).

Mirrors QuantConnect/QuantDinger's thin-MCP pattern: this server holds no logic beyond input validation
+ a vector query (src/search.py). Run with MCP_TRANSPORT=streamable-http for hosted Managed Agents.

STATUS: scaffold.
"""
import os
# from mcp.server.fastmcp import FastMCP
# from .search import search

transport = os.getenv("MCP_TRANSPORT", "stdio")

# mcp = FastMCP("search_knowledge", "Semantic search over the quant research corpus.", host="0.0.0.0")
#
# @mcp.tool()
# async def search_knowledge(query: str, corpus: str | None = None,
#                            tags: list[str] | None = None, k: int = 8) -> list[dict]:
#     """Semantic search over papers / repo notebooks / strategy library / the authoring contract.
#     Returns chunks with citations. See docs/06."""
#     return await search(query, corpus=corpus, tags=tags, k=k)
#
# if __name__ == "__main__":
#     mcp.run(transport=transport)
