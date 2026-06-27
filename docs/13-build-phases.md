# 13 — Build phases

Build in this order. Each phase has a concrete **done-criterion**. Don't move on until it's met — the
early phases de-risk the hard parts (the event→visual pipe; the backtest spine).

## Phase 1 — Skeleton (get the event→visual pipe working)

**Goal:** one round-trip from a session through one MCP tool, with the canvas rendering the live stream.

- `agents/research-manager.agent.yaml`: minimal Manager (model + `agent_toolset`, no roster yet) + one MCP
  (start with `search_knowledge` stub or even QC `list_projects`).
- `agents/environments/cloud.environment.yaml`: `limited` + `allow_mcp_servers: true`.
- `make agents-apply` creates them and prints the IDs into `.env`.
- `orchestrator/`: `sessions.create` → `events.send(user.message)` → SSE consume (patterns 1–3, docs/10) →
  websocket relay.
- `frontend/`: a bare React Flow canvas that adds a node on `session.thread_created` and pulses it on
  status events.

**Done when:** you send a chat message and watch a node appear and light up on the canvas, driven by real
events. This is also your primary debugging surface for everything after.

## Phase 2 — Backtest spine

**Goal:** one strategy through design → compile → backtest → read-results, end to end.

- Self-host the **QC MCP** (`MCP_TRANSPORT=streamable-http`) behind the auth proxy; vault the inbound
  bearer (docs/04, docs/12). Allowlist out live-trading tools.
- `contract/`: write `contract.json` + `strategy_authoring_contract.md` + `validator/validate.py` +
  `templates/starter_algorithm.py`.
- Give the Manager (or a single Modeling+Backtest agent for now) the QC tool allowlist + the contract.
- `frontend/`: wire `BacktestResults.tsx` to `read_backtest` / `read_backtest_chart`.

**Done when:** "backtest this starter strategy" produces a compiled QC backtest and the equity curve +
metrics render in the results panel.

## Phase 3 — Coordinator + file bus

**Goal:** real multiagent delegation, visualized.

- Split into specialists: at minimum Modeling, Backtest, Risk (docs/03). Add the `multiagent` roster to the
  Manager.
- Establish the file-bus contract (`features.parquet` → `algo.py` → `results.json` → `audit.json`).
- `frontend/`: animate delegation/result edges (`agent.thread_message_sent/_received`) and artifact flow.

**Done when:** the canvas shows the Manager delegating to specialists, edges animating, and artifacts
appearing as files move along the bus.

## Phase 4 — Knowledge + iteration

**Goal:** grounded designs + the graded loop + the bias ledger.

- `knowledge/`: ingest SSRN + arXiv + `letianzj/QuantResearch` + QC Strategy Library into the vector DB;
  stand up the `search_knowledge` MCP (docs/06).
- Add FRED/EDGAR/GDELT MCP wrappers (docs/05).
- Implement `user.define_outcome` with the rubric (docs/07); wire `IterationPanel.tsx` to
  `span.outcome_evaluation_*`.
- Stand up the two memory stores (lessons + snooping ledger); wire `BiasLedger.tsx` (docs/08).

**Done when:** a `define_outcome` run iterates against the 5 criteria, the iteration panel converges, and
the ledger shows variants + deflated Sharpe.

## Phase 5 — Full loop + polish

**Goal:** the complete topology + UX.

- Add Paper / Market / Data / Feature / Report agents (docs/03).
- Report agent → PDF/DOCX via Skills to `/mnt/session/outputs/`; orchestrator lists+downloads.
- Web-search idea-gen (Tier-2, Market/Paper only — docs/05).
- Provenance view (`search_knowledge` citations); steering controls (interrupt / approve gated tools).

**Done when:** a full research run — idea → papers → data → features → model → backtest → audit → report —
runs on the canvas with steering and provenance.

## Cross-cutting, do early

- Keep `orchestrator/app/events/schema.py` and the docs/09 bindings table in lockstep.
- Treat the reconnect + idle-gate logic (docs/10) as load-bearing from Phase 1 — retrofitting it is painful.
