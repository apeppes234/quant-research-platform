# 01 — Architecture

## Two planes

Managed Agents splits cleanly into a **control plane** and a **data plane**. Keep this split — it dictates
the repo layout.

| | Control plane | Data plane |
|---|---|---|
| **What** | Agents + environment definitions | Sessions + events (one research run) |
| **How** | Version-controlled YAML, applied via the `ant` CLI | The orchestrator + frontend, via the Anthropic SDK |
| **Cadence** | Once per deploy | Every research run / every turn |
| **Lives in** | [`agents/`](../agents/) | [`orchestrator/`](../orchestrator/) + [`frontend/`](../frontend/) |

**Create agents once, reference by ID per session.** Do not call `agents.create()` in the request path —
that accumulates orphaned agents and defeats versioning. `make agents-apply` runs the control-plane sync;
the orchestrator only ever calls `sessions.create(agent=<id>, ...)`.

## Component map

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ANTHROPIC (Managed Agents) — agent loop, coordinator, subagent threads,   │
│ per-session containers (the "file bus"), memory stores, file storage,     │
│ and the SSE EVENT STREAM.                                                 │
└───────────────▲───────────────────────────────────────┬──────────────────┘
                │ sessions.create / events.send          │ events.stream (SSE)
                │ (Anthropic SDK)                         │
┌───────────────┴─────────────────────────────────────────▼─────────────────┐
│ ORCHESTRATOR  (orchestrator/, Python FastAPI)                              │
│  • creates sessions, sends user.message / user.define_outcome / steering   │
│  • consumes the SSE stream (reconnect-with-consolidation, idle-break gate) │
│  • relays events to the browser over WEBSOCKETS                            │
└───────────────▲─────────────────────────────────────────┬─────────────────┘
                │ websocket                                │ websocket
┌───────────────┴─────────────────────────────────────────▼─────────────────┐
│ FRONTEND (frontend/, React + React Flow)                                   │
│  = a LIVE PROJECTION of the event stream. Canvas, inspector, iteration     │
│    panel, backtest results, bias ledger, chat/steering, provenance.        │
└────────────────────────────────────────────────────────────────────────────┘

  Agents reach tools via MCP (declared on the agent, auth via vaults):
  ┌──────────────┬───────────────────────────────────────────────────────────┐
  │ TOOLS (mcp/) │ search_knowledge (vector DB) · QuantConnect (self-hosted    │
  │ self-hosted  │ official image, streamable-http) · FRED · EDGAR · GDELT ·   │
  │ URL MCPs     │ arXiv. All exposed at PUBLIC HTTPS URLs (see docs/12).      │
  └──────────────┴───────────────────────────────────────────────────────────┘
```

## What runs where

| Layer | Where | Pieces |
|---|---|---|
| **Yours (Docker)** | your host / VPC | frontend + websocket relay; `search_knowledge` MCP + vector DB; ingestion jobs; self-hosted QuantConnect MCP (+ auth proxy); FRED/EDGAR/GDELT/arXiv MCP wrappers; Postgres |
| **Anthropic (Managed)** | Anthropic cloud | agent loop, coordinator, subagent threads, per-session containers, memory stores, file storage, SSE event stream |
| **External** | third parties | QuantConnect cloud (backtests), FRED, EDGAR, GDELT, arXiv |

## The file bus

In a multiagent session, **all agent threads share one container filesystem**. That shared filesystem is
the "file bus": the Data agent writes `features.parquet`, the Modeling agent writes `algo.py`, the
Backtest agent writes `results.json`, the Risk agent reads all of them. Pipeline order (Data → Feature →
Modeling → Backtest → Risk → Report) is enforced by the **Research Manager's instructions + the presence
of files on disk**, not by any hard dependency graph (Managed Agents delegates one level deep only — see
docs/02, docs/03).

## Data flow of one research run

1. User sends a chat message → orchestrator `sessions.create(...)` (or reuse) → `events.send(user.message)`
   or `events.send(user.define_outcome + rubric)`.
2. Research Manager delegates to specialists (one level deep). Each spawns a **thread**; the canvas adds a
   node (`session.thread_created`) and animates a delegation edge (`agent.thread_message_sent`).
3. Specialists call MCP tools (QuantConnect, search_knowledge, …). Node badges update on
   `agent.mcp_tool_use`. Backtests run on QC's cloud; results come back via `read_backtest*`.
4. The grader scores each iteration against the rubric (`span.outcome_evaluation_*`); the iteration panel
   flips criteria ✓/✗.
5. On `satisfied` (or `max_iterations_reached`), the Report agent writes a PDF/DOCX to
   `/mnt/session/outputs/`; the orchestrator lists+downloads it via the Files API.

## Cross-references

- Event stream schema and platform contracts: [`02-managed-agents-platform.md`](02-managed-agents-platform.md)
- Who the agents are: [`03-agent-topology.md`](03-agent-topology.md)
- The SSE→websocket relay specifics: [`10-orchestrator.md`](10-orchestrator.md)
- The UI bindings: [`09-visual-ui.md`](09-visual-ui.md)
