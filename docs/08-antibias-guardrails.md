# 08 — Anti-bias guardrails (the pillar)

Avoiding **look-ahead** and **data-snooping** ("front bias") is the central trust requirement. It's
enforced in four layers, so a failure in one is caught by another.

## 1. Engine

QuantConnect is **point-in-time + survivorship-bias-free** (docs/04). The backtest engine itself won't let
you join future data. No hand-rolled CSVs of "what we know now." This shrinks the look-ahead surface to two
things humans/agents control: the train/holdout split, and the number of variants tried.

## 2. Protocol (enforced at the tool/contract layer)

The authoring contract (docs/11) forces every strategy into:

- **train / validation / sealed holdout** splits, with the **holdout unreachable during design**. The
  Modeling/Feature agents only ever see train+validation; the holdout is evaluated once by the Backtest
  agent and is **tool-layer enforced** (the agents have no tool that returns holdout data during design).
- **walk-forward** evaluation rather than a single in-sample fit.

## 3. Agent

The **Risk / Bias Auditor** runs in a **fresh context window** (its own thread — docs/03) so it isn't
anchored by the Modeling agent's reasoning. It reads `algo.py`, `results.json`, and the data manifest, and
emits `audit.json` with explicit look-ahead findings. Criterion 3 of the rubric requires **zero** findings.

What it checks (non-exhaustive): future-timestamped joins; using `validation`/`holdout` data during
feature construction; survivorship leaks; indicator warm-up that peeks ahead; label leakage; using
revised (non-vintage) macro where ALFRED vintages exist.

## 4. Process — the data-snooping ledger

Every **variant tried** and every **`create_optimization` run** is appended to the **snooping ledger** (a
Managed Agents memory store, docs/02/06). The ledger feeds the **Deflated Sharpe Ratio (DSR)**, which
corrects the observed Sharpe for the number of trials:

- Track `N` = number of independent configurations/iterations evaluated against the holdout.
- DSR deflates the best observed Sharpe by the expected maximum Sharpe under `N` trials of noise; **DSR > 0**
  (rubric criterion 4) means the result survives multiple-testing correction.
- `create_optimization` is **gated `always_ask`** (docs/02) — every sweep is an explicit, logged decision,
  because parameter sweeps are the fastest way to snoop. Walk-forward only.

Ledger entry shape (write from the Risk auditor / orchestrator):

```json
{
  "ts": "ISO-8601",
  "session_id": "...",
  "variant_id": "...",
  "kind": "iteration | optimization",
  "params": { ... },
  "in_sample_sharpe": 1.4,
  "holdout_sharpe": 0.9,
  "trials_to_date": 7
}
```

## The bias / snooping ledger UI

The **Bias / snooping ledger** view (docs/09) renders: variants tried, in-sample vs holdout Sharpe gap per
variant, the running `N`, and the current DSR. This is the auditable trail that the whole system is
honest about overfitting.

## Summary table

| Layer | Mechanism | Defends against |
|---|---|---|
| Engine | QC PIT + survivorship-free | hand-joined future data |
| Protocol | contract: train/val/sealed-holdout + walk-forward, holdout tool-gated | leaking the holdout during design |
| Agent | fresh-context Risk auditor → `audit.json` | subtle look-ahead the builder rationalized |
| Process | snooping ledger → DSR; `create_optimization` gated | multiple-testing / p-hacking |
