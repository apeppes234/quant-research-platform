"""FastMCP server for Phase 4 PIT data-source wrappers."""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

try:
    from .sources import (
        arxiv_qfin_search,
        edgar_company_filings as fetch_edgar_company_filings,
        fred_observations,
        gdelt_doc_search,
    )
except ImportError:  # Allows `uv run src/server.py`.
    from sources import (
        arxiv_qfin_search,
        edgar_company_filings as fetch_edgar_company_filings,
        fred_observations,
        gdelt_doc_search,
    )

service = os.getenv("DATASOURCE_NAME", "all").lower()
transport = os.getenv("MCP_TRANSPORT", "stdio")
port = int(os.getenv("MCP_PORT", "9000"))
mcp = FastMCP(f"{service}_data_sources", host="0.0.0.0", port=port)


def enabled(name: str) -> bool:
    return service in {"all", name}


if enabled("fred"):

    @mcp.tool()
    async def fred_alfred_observations(
        series_id: str,
        observation_start: str | None = None,
        observation_end: str | None = None,
        as_of: str | None = None,
        limit: int = 5000,
    ) -> dict:
        """Return ALFRED vintage observations with an explicit as_of timestamp."""
        return await fred_observations(
            series_id=series_id,
            observation_start=observation_start,
            observation_end=observation_end,
            as_of=as_of,
            limit=limit,
        )


if enabled("edgar"):

    @mcp.tool()
    async def edgar_company_filings(
        cik: str,
        form_type: str | None = None,
        filed_after: str | None = None,
        filed_before: str | None = None,
        as_of: str | None = None,
        limit: int = 50,
    ) -> dict:
        """Return company filings filtered by filing date, never by later knowledge."""
        return await fetch_edgar_company_filings(
            cik=cik,
            form_type=form_type,
            filed_after=filed_after,
            filed_before=filed_before,
            as_of=as_of,
            limit=limit,
        )


if enabled("gdelt"):

    @mcp.tool()
    async def gdelt_documents(
        query: str,
        start_datetime: str,
        end_datetime: str,
        as_of: str | None = None,
        max_records: int = 75,
    ) -> dict:
        """Return timestamped GDELT documents/events for PIT event studies."""
        return await gdelt_doc_search(
            query=query,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            as_of=as_of,
            max_records=max_records,
        )


if enabled("arxiv"):

    @mcp.tool()
    async def arxiv_qfin_papers(query: str, max_results: int = 20, as_of: str | None = None) -> dict:
        """Return arXiv q-fin paper metadata filtered to papers available by as_of."""
        return await arxiv_qfin_search(query=query, max_results=max_results, as_of=as_of)


if __name__ == "__main__":
    mcp.run(transport=transport)
