# 05 — Data layer & trust tiers

The anti-look-ahead boundary is **structural**: data is split into two tiers, and tier membership is
enforced by *which agent gets which MCP tool*.

## Tier 1 — PIT-safe (backtest path)

Point-in-time, survivorship-bias-free, timestamped. Only this tier may influence a backtested strategy.

| Source | What | Access |
|---|---|---|
| **QuantConnect** | prices + fundamentals (survivorship-bias-free, PIT); Dataset Market (timestamped news/sentiment) | self-hosted QC MCP (docs/04) |
| **FRED / ALFRED** | macro time series; **ALFRED = vintage** (as-it-was-known) macro — use ALFRED for PIT | FRED MCP wrapper |
| **SEC EDGAR** | filings by **filing date** (10-K/10-Q/8-K, XBRL financials, Form 4 insider) | EDGAR MCP wrapper |
| **GDELT** | timestamped global event news (PIT-safe for event studies) | GDELT MCP wrapper |

**Who gets Tier 1:** Data, Feature, Modeling, Backtest agents (and the Risk auditor reads the resulting
manifests).

## Tier 2 — Idea-only (walled off)

"As-of-now" context for **idea generation only**. Must **never** reach the backtest. Bound only to the
agents that generate ideas, never to the agents that build/test.

| Source | What | Access |
|---|---|---|
| Built-in `web_search` / `web_fetch` | current web context | `agent_toolset` — **only** on Market + Paper agents |

**Who gets Tier 2:** Market, Paper agents only.

## Explicitly excluded

"As-of-now" REST APIs that reintroduce look-ahead and are redundant with QC: Finnhub, Alpha Vantage,
Polygon snapshots, Tiingo-direct. **Curation over breadth.** The backbone is QuantConnect + FRED + EDGAR;
knowledge is SSRN + arXiv + QuantResearch repo + QC Strategy Library; idea-gen is web search.

## How the boundary is enforced

1. **Tool binding** — Tier-2 tools are simply not in the Modeling/Backtest/Data/Feature agents' tool sets.
2. **PIT guards in the wrappers** — the FRED wrapper defaults to ALFRED vintages; the EDGAR wrapper filters
   by filing date; each PIT pull writes a **data manifest** (source, as-of timestamp) to the file bus.
3. **The validator** rejects any hand-joined future data (docs/11), and the **Risk auditor** independently
   checks the data manifest for as-of violations (docs/08).

## MCP servers to build for this tier (Phase 4/5)

- `mcp/data-sources/fred/`   — FRED + ALFRED (vintage). Needs `FRED_API_KEY`.
- `mcp/data-sources/edgar/`  — SEC EDGAR full-text + XBRL, by filing date. Needs a descriptive
  `SEC_EDGAR_USER_AGENT` (EDGAR requires it).
- `mcp/data-sources/gdelt/`  — GDELT events/GKG (keyless).
- `mcp/data-sources/arxiv/`  — arXiv q-fin metadata + PDFs (keyless) — this one is knowledge-tier (docs/06),
  bound to the Paper agent.

All are self-hosted `streamable-http` URL MCPs (docs/12). QC is the only Tier-1 source that ships its own
MCP image; the rest are thin wrappers you write (mirror the QuantDinger MCP-over-REST pattern).
