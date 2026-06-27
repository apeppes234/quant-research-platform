# mcp/data-sources — thin MCP wrappers over PIT/knowledge data APIs

Four small FastMCP servers (build at Phase 4/5). Same shape as `mcp/knowledge` (FastMCP, `host="0.0.0.0"`,
`MCP_TRANSPORT=streamable-http`, auth proxy + vault bearer). Recommendation (docs/14 O4): **one shared
FastMCP codebase**, deployed as four services — but separate dirs keep concerns clear.

| Dir | Source | Tier (docs/05) | Notes |
|---|---|---|---|
| [`fred/`](fred/) | FRED + **ALFRED** | PIT-safe | Use ALFRED **vintages** (as-it-was-known) for anything that enters a backtest. Needs `FRED_API_KEY`. |
| [`edgar/`](edgar/) | SEC EDGAR | PIT-safe | Filter by **filing date**; 10-K/10-Q/8-K, XBRL, Form 4. Needs a descriptive `SEC_EDGAR_USER_AGENT`. |
| [`gdelt/`](gdelt/) | GDELT | PIT-safe | Timestamped global events/GKG. Keyless. |
| [`arxiv/`](arxiv/) | arXiv q-fin | knowledge | Metadata + PDFs for the Paper agent + ingestion. Keyless. |

Each must write/honor PIT semantics: the FRED wrapper defaults to vintage; the EDGAR wrapper filters by
filing date; both surface the as-of timestamp so the Data agent can record it in the data manifest
(docs/05, docs/08).
