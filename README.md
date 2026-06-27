# Quant Research Platform

A **Claude-powered quant research assistant** with a highly visual, agentic UI. You chat with a
**Research Manager** agent; it orchestrates a team of specialist agents that read papers + reference
code, design strategies, backtest them on **QuantConnect**, audit them for look-ahead/data-snooping
bias, and iterate against a rubric until they pass — and you watch the whole thing happen **live on an
agent-graph canvas**.

> **No brokerage. No live trading.** This is a research/backtesting tool only. Every QuantConnect
> live-trading tool is deliberately allowlisted *out* (see [`docs/04-quantconnect.md`](docs/04-quantconnect.md)).

---

## ⚠️ Read this first (especially if you are an LLM picking up this repo)

This repository is currently a **documented scaffold** — directories and stub files with detailed
header comments, plus a complete `docs/` set. **Almost no functional code is implemented yet.** Your job,
when building, is to fill in the stubs following the contracts described in the docs.

**Start here, in order:**

1. [`docs/00-overview.md`](docs/00-overview.md) — the vision and the one guiding principle.
2. [`docs/01-architecture.md`](docs/01-architecture.md) — the whole system on one page.
3. [`docs/14-decisions.md`](docs/14-decisions.md) — what's been decided and *why* (and what's still open).
4. The `README.md` inside whichever component you're working on (`orchestrator/`, `frontend/`,
   `agents/`, `mcp/`, `contract/`, `knowledge/`).

**Do not invent platform behavior.** This system is built on Anthropic's **Managed Agents** product and
**QuantConnect's** API. Both have specific, verified contracts documented here
([`docs/02-managed-agents-platform.md`](docs/02-managed-agents-platform.md),
[`docs/04-quantconnect.md`](docs/04-quantconnect.md)). When a detail isn't in the docs, consult the live
sources those docs link to — don't guess.

---

## The guiding principle (from the QuantDinger template)

**Constrain → validate → run.** Expertise lives in a *strategy authoring contract* + a *validator* + a
*curated reference library* — **not** in a giant prompt. Free-form natural language never reaches the
backtest engine. See [`contract/`](contract/) and [`docs/11-authoring-contract.md`](docs/11-authoring-contract.md).

---

## System at a glance

```
            You ──chat──▶  Research Manager (coordinator, Claude Opus 4.8)
                               │ delegates ONE level deep (Managed Agents constraint)
                               ▼
        ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
      Paper      Market      Data      Feature   Modeling   Backtest   Risk/Report
      agent      agent      agent      agent      agent      agent      agents
        └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
                               │ shared container filesystem = "file bus"
                               ▼
                     QuantConnect (backtests) · search_knowledge (vector DB)
                     FRED · EDGAR · GDELT · arXiv  (all self-hosted URL MCPs)

   Anthropic Managed Agents  ──SSE event stream──▶  Orchestrator (FastAPI)
                                                         │ websocket relay
                                                         ▼
                                                   Frontend (React + React Flow)
                                                   = a LIVE projection of the event stream
```

| Component | What it is | Tech | Plane |
|---|---|---|---|
| [`agents/`](agents/) | Versioned agent + environment definitions | YAML, applied via `ant` CLI | **Control plane** (once per deploy) |
| [`orchestrator/`](orchestrator/) | Subscribes to the Managed Agents SSE stream, relays to the browser over websockets, handles steering | Python / FastAPI | **Data plane** (every run) |
| [`frontend/`](frontend/) | The live agent-graph canvas + inspector + iteration/backtest/ledger panels | React + React Flow + Vite + TS | Data plane |
| [`mcp/`](mcp/) | Self-hosted MCP servers: `search_knowledge`, QuantConnect (self-hosted official image), FRED/EDGAR/GDELT/arXiv | Python (FastMCP), Docker | Tools |
| [`contract/`](contract/) | The strategy authoring contract + validator (the "expertise" layer) | Markdown + JSON + Python | Expertise |
| [`knowledge/`](knowledge/) | Ingestion jobs feeding the vector DB (SSRN, arXiv, QuantResearch repo, QC Strategy Library) | Python | Knowledge |
| [`infra/`](infra/) | docker-compose, Postgres init, env templates | Docker / SQL | Infra |

**What runs where:**

- **Yours (Docker):** frontend + websocket relay; `search_knowledge` MCP + vector DB; ingestion jobs;
  self-hosted QuantConnect MCP (+ auth proxy); other data-source MCP wrappers; Postgres.
- **Anthropic (Managed):** the agent loop, coordinator, subagent threads, per-session containers,
  memory stores, file storage, and the SSE event stream.
- **External:** QuantConnect cloud, FRED, EDGAR, GDELT, arXiv.

See [`docs/01-architecture.md`](docs/01-architecture.md) for the full breakdown.

---

## Build phases (see [`docs/13-build-phases.md`](docs/13-build-phases.md))

1. **Skeleton** — Research Manager agent + cloud env + a session round-tripping one MCP tool + a bare
   canvas that renders the SSE stream (nodes light up). *Get the event→visual pipe working first.*
2. **Backtest spine** — self-hosted QC MCP + vault + authoring contract + validator; one strategy through
   design → compile → backtest → read-results, with the results panel wired.
3. **Coordinator + file bus** — add Modeling/Backtest/Risk specialists; animate delegation edges + artifact flow.
4. **Knowledge + iteration** — ingest corpora; add FRED/EDGAR/GDELT MCPs; `define_outcome` loop + iteration panel; bias auditor + ledger.
5. **Full loop + polish** — Paper/Market/Data agents, Report agent, web-search idea-gen, provenance view, steering controls.

---

## Quickstart (target state — not yet runnable)

```bash
cp .env.example .env            # fill in ANTHROPIC_API_KEY, QC creds, etc.
make agents-apply               # create/update agents + environment via `ant` (control plane)
make up                         # docker-compose: postgres, vector DB, MCPs, orchestrator, frontend
# open http://localhost:5173    # the canvas
```

See the [`Makefile`](Makefile) for individual targets and [`docs/13-build-phases.md`](docs/13-build-phases.md)
for what's actually wired at each phase.

---

## Status

🟡 **Scaffold only.** Structure + docs complete; implementation not started. Pick up from
[`docs/13-build-phases.md`](docs/13-build-phases.md) Phase 1.
