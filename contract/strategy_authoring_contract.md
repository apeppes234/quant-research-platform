# Strategy Authoring Contract (v1)

> The Modeling agent MUST follow this. Free-form natural language never reaches the backtest engine — this
> contract + the validator are how that's enforced (docs/00, docs/08, docs/11). The machine-readable copy
> is `contract.json`; keep the two in sync.

## 1. Workflow (in order)

1. Retrieve relevant patterns via `search_knowledge` (corpus = `contract`, `repo`, `strategy_library`).
2. Start from `templates/starter_algorithm.py`.
3. Write `/workspace/algo.py` (a QuantConnect `QCAlgorithm` subclass).
4. **Run the validator (`validator/validate.py`) — it MUST pass before you compile.**
5. QC `create_compile` + `read_compile` — **fix ALL compile warnings**.
6. `create_backtest` on **train + validation only**.
7. Evaluate the **sealed holdout EXACTLY ONCE**.
8. Write `/workspace/results.json` and copy the same JSON to `/mnt/session/outputs/results.json` with
   **both** in-sample and sealed-holdout segments (each with Sharpe, max drawdown, total return, equity
   curve, and drawdown).
9. Hand off to the Risk auditor.

## 2. Required structure

- Three time splits: **train / validation / sealed holdout**. The holdout is **sealed during design** —
  you must not read holdout data while building features or fitting. (Tool-layer + validator enforced.)
- **Walk-forward** evaluation, not a single in-sample fit.
- Entry/exit logic lives in `on_data` (event-driven); no peeking at future bars.
- `results.json` carries both segments so the rubric (docs/07) can compute the in-sample/holdout gap and
  the Deflated Sharpe.
- The Phase 2 starter uses:
  - train: `2010-01-01` through `2017-12-31`
  - validation: `2018-01-01` through `2019-12-31`
  - sealed holdout: `2020-01-01` through `2023-12-31`

## 3. Forbidden

- Natural language in code (the body must be valid Python).
- `import os | sys | subprocess | requests`; `eval`/`exec`; any arbitrary file/network IO outside QC APIs.
- Reading validation/holdout data during feature construction.
- Hand-joined future-timestamped data — use QuantConnect PIT data only.
- Overwriting QC indicator method names — use `self._rsi = self.rsi(self._symbol, 14)`, never `self.rsi = ...`.
- `create_optimization` without an approved, ledgered request (it's `always_ask` gated — docs/08).

## 4. Results JSON shape

The browser expects this shape. The Backtest agent must write it to `/workspace/results.json` and copy it
to `/mnt/session/outputs/results.json` for the orchestrator file bridge:

```json
{
  "project_id": "string",
  "backtest_id": "string",
  "strategy": "StarterStrategy",
  "segments": {
    "in_sample": {
      "start": "2010-01-01",
      "end": "2019-12-31",
      "metrics": { "sharpe": 0.0, "max_drawdown": 0.0, "total_return": 0.0 },
      "equity_curve": [{ "time": "2010-01-04", "value": 100000.0 }],
      "drawdown": [{ "time": "2010-01-04", "value": 0.0 }]
    },
    "holdout": {
      "start": "2020-01-01",
      "end": "2023-12-31",
      "metrics": { "sharpe": 0.0, "max_drawdown": 0.0, "total_return": 0.0 },
      "equity_curve": [{ "time": "2020-01-02", "value": 100000.0 }],
      "drawdown": [{ "time": "2020-01-02", "value": 0.0 }]
    }
  }
}
```

## 5. QuantConnect idioms (docs/04)

- Create projects via `create_project` (don't write project files locally).
- PEP8 snake_case; use `update_code_to_pep8` if needed.
- Compile and fix warnings **before** backtesting; prefer `patch_file` for small edits.

## 6. The rubric (success criteria — single source of truth, mirrored in docs/07)

A candidate is **`satisfied`** only if **all five** pass:

1. **Holdout Sharpe > 1.0** (sealed out-of-sample).
2. **|in-sample Sharpe − holdout Sharpe| < 0.5** (overfit guard).
3. **Zero look-ahead findings** from the Risk auditor (`audit.json`).
4. **Deflated Sharpe Ratio > 0** (corrected for # variants tried — snooping ledger, docs/08).
5. **Max drawdown < 25%**.

`max_iterations` = 5. Every iteration that touches the holdout is logged to the snooping ledger and counts
toward the Deflated-Sharpe trial count.
