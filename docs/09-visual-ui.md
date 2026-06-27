# 09 — Visual UI

The UI is a **live projection of the Managed Agents event stream**. Every visual element binds to a
concrete event, so the picture is true by construction. Library: **React Flow** for the canvas (decision
in docs/14). Frontend lives in [`frontend/`](../frontend/).

## Event → visual bindings (the contract between orchestrator and UI)

| Visual element | Driven by event |
|---|---|
| Agent node appears on the canvas | `session.thread_created` |
| Node pulses "working" / settles "idle" | `session.thread_status_running` / `_idle` |
| Edge animates (Manager → specialist, and results back) | `agent.thread_message_sent` / `_received` |
| Node badge shows current action ("compiling on QC", "searching papers") | `agent.tool_use` / `agent.mcp_tool_use` |
| "Thinking…" shimmer | `agent.thinking` |
| Token / cost meter | `span.model_request_start` / `_end` (`model_usage`) |
| Rubric criteria flip ✓/✗; iteration counter ticks | `span.outcome_evaluation_start` / `_end` (`result`, `iteration`) |
| File-bus artifacts (`features.parquet`, `algo.py`, `results.json`) moving between nodes | container file writes surfaced by the agents (and `agent.tool_use` on `write`) |

> The orchestrator does NOT invent state — it forwards normalized events and the frontend reduces them.
> The normalization map lives in [`orchestrator/app/events/schema.py`](../orchestrator/app/events/schema.py)
> and must stay in sync with this table.

## The 7 core views (each = one component in `frontend/src/views/`)

1. **Agent-graph canvas** (`AgentGraphCanvas.tsx`) — the topology, alive. Nodes light by status, edges
   animate on delegation/results, artifacts flow along the file bus. Custom node = `AgentNode.tsx`, custom
   edge = `DelegationEdge.tsx`.
2. **Agent inspector** (`AgentInspector.tsx`) — click a node → that thread's stream: summarized thinking,
   tool calls, outputs. Backed by the per-thread stream (`threads.events.stream`, docs/02).
3. **Iteration panel** (`IterationPanel.tsx`) — the `define_outcome` loop made visible: the 5 rubric
   criteria (docs/07) with per-criterion pass/fail converging across iterations.
4. **Backtest results** (`BacktestResults.tsx`) — equity curve, drawdown, trades, metrics from QC
   `read_backtest` / `read_backtest_chart` / `read_backtest_orders`. (Reuse QuantDinger's panel *design* as
   reference — the QuantDinger Vue source isn't available, so rebuild in React; see docs/14.)
5. **Bias / snooping ledger** (`BiasLedger.tsx`) — variants tried, deflated Sharpe, in-sample vs holdout
   gap (docs/08).
6. **Chat + steering** (`ChatSteering.tsx`) — the Research Manager conversation; interrupt
   ("stop/redirect" → `user.interrupt`), approve gated tools (`always_ask` → `user.tool_confirmation`).
7. **Provenance** (`ProvenanceView.tsx`) — which papers / repo notebooks / datasets a design drew on
   (from `search_knowledge` citations, docs/06).

## State flow in the frontend

```
websocket (from orchestrator) → ws.ts (dedupe by event id) → sessionStore.ts (reducer)
  → views subscribe to slices of the store
```

- **Dedupe by event `id`** in `ws.ts` (the orchestrator may resend on reconnect — docs/10).
- The reducer in `sessionStore.ts` maintains: `threads{}` (node status), `edges[]` (animations), `tokens`
  (cost meter), `outcome{iteration, criteria[]}`, `backtest{}`, `ledger[]`, `chat[]`, `provenance[]`.

## Charting

For the backtest panels, pick a charting lib at implementation time (candidates: `lightweight-charts`
(TradingView) for the equity/price series, `Recharts` for metrics). Record the choice in docs/14. Keep the
equity curve + drawdown as the two hero charts.
