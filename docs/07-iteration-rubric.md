# 07 — Iteration & rubric

The iteration engine is the Managed Agents `user.define_outcome` loop (docs/02): **design → backtest →
grade → revise** against a rubric until it passes, hits `max_iterations`, or is interrupted. A separate
grader (independent context window) scores each iteration; the **iteration panel** (docs/09) renders the
loop converging.

## The rubric = the bias + performance gates

These are the agreed defaults (confirm/adjust in docs/14). The rubric is **markdown with explicit,
independently gradeable criteria** — the grader scores each one separately, so each must be checkable from
the artifacts on the file bus (`results.json`, `audit.json`, the data manifest, the snooping ledger).

| # | Criterion | Pass condition | Checked from |
|---|---|---|---|
| 1 | **Out-of-sample performance** | Sealed-holdout **Sharpe > 1.0** | `results.json` (holdout segment) |
| 2 | **Overfit guard** | **\|in-sample Sharpe − holdout Sharpe\| < 0.5** | `results.json` (both segments) |
| 3 | **Look-ahead audit** | **Zero** look-ahead findings from the Risk auditor | `audit.json` |
| 4 | **Multiple-testing correction** | **Deflated Sharpe Ratio > 0** (corrected for # variants tried) | `results.json` + snooping ledger |
| 5 | **Tail risk** | **Max drawdown < 25%** | `results.json` |

A candidate must satisfy **all five** to be `satisfied`.

`max_iterations`: **default 3** (max 20); raise it only when a run genuinely needs more convergence room.
Too many iterations against a fixed holdout is
itself a snooping risk — every iteration that touches the holdout must be logged to the ledger and counted
in the deflated-Sharpe denominator (docs/08).

## The rubric file

The canonical rubric lives at [`contract/strategy_authoring_contract.md`](../contract/strategy_authoring_contract.md)
(rubric section) and is also emitted as a standalone markdown the orchestrator passes in
`user.define_outcome.rubric`. Keep the numbers in **one** place and reference them — don't duplicate.

## How a run is graded

1. Orchestrator: `events.send(user.define_outcome{description, rubric, max_iterations:5})`.
2. Manager delegates the pipeline (docs/03); Backtest agent writes `results.json` with **both** in-sample
   and sealed-holdout segments; Risk auditor writes `audit.json` + updates the ledger.
3. `span.outcome_evaluation_start{iteration}` → grader scores criteria 1–5 → `span.outcome_evaluation_end
   {result, explanation, iteration}`.
4. `needs_revision` → Manager re-delegates a revision (and the ledger increments). `satisfied` /
   `max_iterations_reached` / `failed` → session idles; Report agent produces the deliverable.

## UI mapping

- Each criterion is a row in the **iteration panel**; it flips ✓/✗ on each `span.outcome_evaluation_end`.
- The **iteration counter** ticks with `iteration`.
- The grader's `explanation` is shown per row so the user sees *why* a criterion failed.

See docs/09 for the exact bindings and docs/08 for the deflated-Sharpe math behind criterion 4.
