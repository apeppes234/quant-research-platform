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
| Provenance citations appear | `agent.mcp_tool_result` for `search_knowledge`, normalized as `provenance.add` |
| Bias ledger updates | local memory-store writes under `/mnt/memory/*snooping*`, normalized as `ledger.entry` |
| Gated tool approval appears | `agent.tool_use` / `agent.mcp_tool_use` with `evaluated_permission=="ask"`, normalized as `tool.confirmation.requested` |
| Backtest metrics/equity/drawdown update | QC `agent.mcp_tool_result` for `read_backtest*` normalized as `backtest.update`, plus `/mnt/session/outputs/results.json` |
| File-bus artifacts (`features*.parquet`, `data_manifest.json`, `algo.py`, `results.json`, `audit.json`, `report.pdf`) moving between nodes | `agent.tool_use` on local `write`/`edit` normalized as `artifact.write` |
| Downloadable final report appears | Files API lists `/mnt/session/outputs/report.pdf`; frontend polls `/api/sessions/{id}/report` |

> The orchestrator does NOT invent state — it forwards normalized events and the frontend reduces them.
> The normalization map lives in [`orchestrator/app/events/schema.py`](../orchestrator/app/events/schema.py)
> and must stay in sync with this table.

## The 8 core views (each = one component in `frontend/src/views/`)

1. **Agent-graph canvas** (`AgentGraphCanvas.tsx`) — the topology, alive. Nodes light by status, edges
   animate on delegation/results, artifacts flow along the file bus. `artifact.write` events produce
   traveling chips on `DelegationEdge.tsx`.
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
   The left sidebar carries two tabs: **Steering** (chat/interrupt/approvals) and **Research**.
6b. **Research sources** (`ResearchSourceTab.tsx`, in the left sidebar) — an inspectable view of the
   sources agents actually used, grouped by provider (arXiv / SSRN / QuantResearch / QuantConnect
   Strategy Library). Each card shows title/citation, provider, source link, the snippet the agent
   relied on, and metadata badges (corpus, strategy family / asset class / signal type, notebook cell,
   page). arXiv (and SSRN where a PDF exists) render in an embedded PDF viewer (`PaperPdfViewer.tsx`)
   with a dropdown to switch between referenced papers; local PDFs are served by the sandboxed
   `/api/pdfs` route (approved directories only). When no PDF exists it falls back to the source link.
7. **Provenance** (`ProvenanceView.tsx`) — a compact citation list in the right-hand analysis lane
   (the Research tab above is the full inspectable viewer; both read the same `provenance[]`, docs/06).
8. **Report** (`ReportDeliverable.tsx`) — final `report.pdf` status and download link from the session
   Files API.

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
