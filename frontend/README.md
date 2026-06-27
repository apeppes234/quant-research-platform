# frontend/ — The live agent-graph UI (React + React Flow + Vite + TS)

A **live projection of the Managed Agents event stream** (relayed by the orchestrator over a websocket).
Every visual element binds to a concrete event — see the bindings table in
[`docs/09-visual-ui.md`](../docs/09-visual-ui.md).

## Run

```bash
npm install
npm run dev        # http://localhost:5173  (or: make frontend)
```

Connects to the orchestrator websocket at `WS /sessions/{id}/stream`.

## Data flow

```
orchestrator websocket → src/api/ws.ts (dedupe by event id)
                       → src/store/sessionStore.ts (reducer over {kind,payload})
                       → views subscribe to slices
```

The reducer consumes exactly the `kind`s defined in `orchestrator/app/events/schema.py`. **Keep them in
sync** — a new event kind means a new case here and a new mapping there, together.

## The 7 views (`src/views/`)

| View | Driven by | Notes |
|---|---|---|
| `AgentGraphCanvas.tsx` | `node.add`, `node.status`, `edge.animate`, `node.badge` | React Flow; custom `AgentNode` + `DelegationEdge` |
| `AgentInspector.tsx` | per-thread stream | click a node → its thinking/tools/output |
| `IterationPanel.tsx` | `rubric.start` / `rubric.end` | the 5 gates flip ✓/✗; iteration counter |
| `BacktestResults.tsx` | QC `read_backtest*` data | equity curve, drawdown, trades, metrics |
| `BiasLedger.tsx` | snooping ledger | variants, in-sample vs holdout gap, Deflated Sharpe |
| `ChatSteering.tsx` | `agent.text` + sends interrupt/confirm | the Manager conversation + steering |
| `ProvenanceView.tsx` | `search_knowledge` citations | which papers/notebooks/datasets a design used |

## Stack choices (docs/14)

- **React Flow** for the canvas (D4): native custom nodes + animated edges.
- Charting for `BacktestResults`: pick at Phase 2 (candidates: `lightweight-charts`, `Recharts`) — O3 in docs/14.
- State: a small store (Zustand or Context+reducer). Keep the reducer pure and keyed off `{kind}`.

STATUS: scaffold — components are stubs with the intended props/bindings documented.
