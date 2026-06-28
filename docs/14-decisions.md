# 14 — Decisions (ADR-style)

Lightweight record of what's decided and **why**, plus what's still open. Update this when you make a call
so the next person (or LLM) doesn't re-litigate it.

## Decided

### D1 — Orchestration: Anthropic Managed Agents (not a custom loop)
Hosted agent loop + coordinator/subagent model + memory stores + `define_outcome` + a single SSE event
stream the UI can render 1:1. Heavy compute (backtests) runs on QC anyway. See docs/00, docs/02.

### D2 — QuantConnect MCP: self-host the official image in `streamable-http` mode
**Verified from source** that `QuantConnect/mcp-server` supports `MCP_TRANSPORT=streamable-http` (not
stdio-only as previously assumed). So we self-host the official Docker image as a URL MCP — no custom
bridge. Live-trading tools are allowlisted out. See docs/04. *Supersedes the earlier "stdio → host-side
bridge" idea, which is now unnecessary.*

### D3 — QC endpoint auth: auth proxy + vault `static_bearer`
QC's MCP has no inbound auth and uses its own env creds to reach QC. So QC creds stay as container env; an
nginx proxy enforces an inbound bearer; that bearer goes in an Anthropic vault keyed to the URL. Same
pattern for all self-hosted MCPs. See docs/12.

### D4 — Canvas library: React Flow
React-native custom nodes + animated edges fit the status-pulse / delegation-edge use case with the least
glue, and pair cleanly with the React frontend. (Cytoscape considered; better for very large auto-laid-out
graphs than our fixed ~9-node animated pipeline.) See docs/09.

### D5 — Orchestrator language: Python / FastAPI
Reuses QuantDinger's proven patterns (Postgres-backed async jobs, SSE handling, MCP-over-REST thin
wrappers — all Python) and matches the Anthropic Python SDK. The frontend stays React/TS; the boundary is
the websocket. See docs/10.

### D6 — Iteration rubric (the 5 gates)
Holdout Sharpe > 1.0; |in-sample − holdout Sharpe| < 0.5; zero look-ahead findings; Deflated Sharpe > 0;
max drawdown < 25%. `max_iterations` = 5. Reasonable defaults — tune against real runs. See docs/07.

### D7 — Trust tiers are tool-enforced
PIT-safe sources (QC/FRED-ALFRED/EDGAR/GDELT) only on the build/test agents; idea-only web search only on
Market/Paper. Finnhub + other "as-of-now" REST APIs excluded. See docs/05.

### D8 — Expertise = contract + validator + library (not a big prompt)
Carried over from QuantDinger. Free-form NL never reaches the backtest engine; the validator is the
tool-layer enforcement of the anti-look-ahead protocol. See docs/11, docs/08.

### D9 — Repo shape: documented scaffold first
Structure + heavy docs now; implementation later, possibly by a different LLM without this conversation's
context. Hence every doc is self-contained and the "verified" claims cite primary sources.

### D10 — Backtest charting: Recharts v3
Phase 2 uses Recharts v3 for equity, drawdown, and compact metric visuals in `BacktestResults.tsx`. It is
lighter glue for mixed dashboard charts than pairing `lightweight-charts` with a separate metrics library;
the results panel is strategy-performance oriented, not a full trading terminal.

### D11 — Knowledge embeddings: `intfloat/e5-small-v2` (384d), self-hosted
Phase 4 freezes the vector dimension at 384 and records the embedding model in chunk metadata. The local
hash embedder exists only for deterministic offline tests/dry-runs; production ingestion should use the
frozen local model so re-embedding is not accidental.

### D12 — Data-source MCP wrappers: one shared FastMCP codebase, separate services
FRED/ALFRED, EDGAR, GDELT, and arXiv use `mcp/data-sources/shared` with `DATASOURCE_NAME` selecting the
tool surface. Each service is fronted by the bearer proxy pattern and attached through vaults.

### D13 — Report and steering bridge: Managed Agents events + Files API
Phase 5 keeps human-in-the-loop control on the event stream: `user.interrupt` for stop/redirect and
`user.tool_confirmation` keyed by the triggering event id for gated tools. Final report delivery uses
`/mnt/session/outputs/report.pdf` plus `files.list(scope_id=session.id)` / `files.download(id)`, exposed by
the orchestrator as session output routes.

## Open (decide at implementation time; record the answer here)

| ID | Question | Notes / leaning |
|---|---|---|
| O1 | **Vector DB**: pgvector vs Qdrant | pgvector keeps it in the existing Postgres (one fewer service); Qdrant scales better. Default pgvector. |
| O2 | **Embedding model** | Decided in D11: `intfloat/e5-small-v2`, 384d. |
| O3 | **Backtest charting lib** | Decided in D10: Recharts. |
| O4 | **Data-source MCP wrappers** | Decided in D12: one shared FastMCP codebase, separate deployments. |
| O5 | **Rubric numbers** | D6 defaults are unconfirmed against real strategies — revisit after Phase 4. |
| O6 | **Hosting / tunnel for MCPs in dev** | cloudflared vs ngrok for exposing local MCPs at public HTTPS. See docs/12. |
| O7 | **Tutorials/Documentation licensing** | QC repos are Apache-2.0-ish but confirm terms before redistributing ingested Strategy Library text. |

## Reference: relationship to QuantDinger

QuantDinger (`~/QuantDinger`) is the structural template. **Reused as patterns:** the thin MCP-over-REST
wrapper, the contract→validate→run discipline, the Postgres-backed submit-and-poll job model, the
agent-token scoping idea, the Fernet credential pattern, the Docker layout. **Not reusable:** its frontend
(Vue, lives in a separate private repo — so all UI is rebuilt in React here), its trading-domain data
sources, and its `qd_*` schema.
