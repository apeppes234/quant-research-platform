# mcp/data-sources — thin MCP wrappers over PIT/knowledge data APIs

Four small FastMCP services from one shared codebase. Same shape as `mcp/knowledge` (FastMCP,
`host="0.0.0.0"`, `MCP_TRANSPORT=streamable-http`, auth proxy + vault bearer). Decision D12: **one shared
FastMCP codebase**, deployed as separate services with `DATASOURCE_NAME`.

| Dir | Source | Tier (docs/05) | Notes |
|---|---|---|---|
| [`shared/`](shared/) with `DATASOURCE_NAME=fred` | FRED + **ALFRED** | PIT-safe | Use ALFRED **vintages** (as-it-was-known) for anything that enters a backtest. Needs `FRED_API_KEY`. |
| [`shared/`](shared/) with `DATASOURCE_NAME=edgar` | SEC EDGAR | PIT-safe | Filter by filing date. Needs `SEC_EDGAR_USER_AGENT`. |
| [`shared/`](shared/) with `DATASOURCE_NAME=gdelt` | GDELT DOC | PIT-safe | Timestamped global event/news pulls. Keyless. |
| [`shared/`](shared/) with `DATASOURCE_NAME=arxiv` | arXiv q-fin | knowledge-tier | Metadata/PDF discovery for ingestion and Paper agent grounding. Keyless. |

The shared FastMCP implementation is deployed as separate streamable-http services and fronted by the same
bearer auth proxy pattern as QuantConnect. Every response includes an `as_of` timestamp and citation-like
source string so the Data agent can write a point-in-time `data_manifest.json`.

Each must write/honor PIT semantics: the FRED wrapper defaults to vintage; the EDGAR wrapper filters by
filing date; both surface the as-of timestamp so the Data agent can record it in the data manifest
(docs/05, docs/08).
