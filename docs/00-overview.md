# 00 — Overview

## Vision

A Claude-powered quant research assistant with a highly visual, user-friendly interface. You chat with a
**Research Manager**; it orchestrates a team of specialist agents that:

1. read academic papers + reference code,
2. design candidate trading strategies,
3. backtest them on **QuantConnect** (point-in-time, survivorship-bias-free),
4. audit them for look-ahead / data-snooping bias, and
5. iterate against a rubric until they pass —

and you **watch the whole thing happen live on an agent-graph canvas**.

**No brokerage. No live trading.** Research and backtesting only.

## The one guiding principle: constrain → validate → run

Borrowed from the QuantDinger project (the structural template this repo is modeled on):

> **Expertise lives in a strategy authoring contract + a validator + a curated reference library — not in
> a giant prompt. Free-form natural language never reaches the backtest engine.**

Concretely:

- A **contract** ([`contract/`](../contract/)) tells the Modeling agent exactly how a valid strategy must
  be structured (required signal columns, train/validation/sealed-holdout split, forbidden imports,
  walk-forward protocol).
- A **validator** statically checks generated code against that contract *before* it is ever compiled or
  backtested. This is where anti-look-ahead rules are mechanically enforced.
- A **reference library** (vector DB of papers + canonical strategy notebooks) grounds designs in known
  patterns instead of letting the model improvise.

Everything else in this system is in service of that loop being **observable** (the live canvas) and
**trustworthy** (the bias guardrails).

## Why Managed Agents (not a custom loop)

The orchestration runs on Anthropic's **Managed Agents** product: Anthropic hosts the agent loop, the
coordinator, the subagent threads, the per-session containers, memory stores, and emits a single **SSE
event stream**. We accept that the loop runs on Anthropic infra (the heavy compute — backtests — runs on
QuantConnect's cloud anyway). In exchange we get: versioned agent configs, a built-in coordinator/subagent
model, persistent memory, a rubric-graded iteration engine (`define_outcome`), and — crucially — an event
stream that the UI can render **1:1**, so the picture on screen is true by construction.

See [`docs/02-managed-agents-platform.md`](02-managed-agents-platform.md).

## What's deliberately cut (vs. QuantDinger)

Live/paper trading + brokerage (IBKR/MT5), the multi-provider market-data layer (yfinance/finnhub/crypto),
notifications/OAuth/payments. **Kept:** constrain→validate→run, the MCP pattern, the async job model, the
strategy-library concept, the Docker layout, and the backtest-results UI panels (reused as design
reference). See [`docs/14-decisions.md`](14-decisions.md).
