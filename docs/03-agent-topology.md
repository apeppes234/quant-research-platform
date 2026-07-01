# 03 — Agent topology

**Flattened** because Managed Agents delegates one level only (docs/02). The **Research Manager** is the
sole coordinator; the eight specialists are leaves in its roster. Pipeline order (Market/Paper → Data →
Feature → Modeling → Backtest → Risk → Report) is driven by the Manager's `system` instructions + the shared
container filesystem (the "file bus"), **not** by nested delegation.

Each agent below maps to one YAML file in [`agents/`](../agents/). Models follow the latest-capable
default (`claude-opus-4-8`) unless a cheaper tier is clearly adequate.

| Agent | YAML | Model | Tools (high level) | Role |
|---|---|---|---|---|
| **Research Manager** (coordinator + chat) | `research-manager.agent.yaml` | `claude-opus-4-8` | `agent_toolset`, `multiagent` roster, memory stores | Talks to the user; delegates one level; owns pipeline order; runs `define_outcome`. |
| **Paper agent** | `specialists/paper.agent.yaml` | `claude-haiku-4-5` → escalate to `opus-4-8` for deep reads | `search_knowledge` MCP, arXiv/SSRN MCP, `web_fetch`, PDF read | Turns papers into testable hypotheses. |
| **Market agent** | `specialists/market.agent.yaml` | `claude-sonnet-4-6` | QC datasets, FRED MCP, GDELT MCP, `web_search` (idea-gen) | Surfaces ideas / current context (IDEA-ONLY tier). |
| **Data agent** | `specialists/data.agent.yaml` | `claude-haiku-4-5` | QC history/datasets MCP, FRED/ALFRED, EDGAR (PIT-guarded) | Pulls point-in-time data; writes `features.parquet` etc. |
| **Feature agent** | `specialists/feature.agent.yaml` | `claude-sonnet-4-6` | QC Jupyter/QuantBook cells, `search_knowledge` | Builds features in PIT research; validates signal quality. |
| **Modeling agent** | `specialists/modeling.agent.yaml` | `claude-opus-4-8` (high effort) | **contract + validator**, `search_knowledge`, QC `create_compile` | Authors `algo.py` to the contract; self-validates before compile. |
| **Backtest agent** | `specialists/backtest.agent.yaml` | `claude-sonnet-4-6` | QC `create_backtest` / `read_backtest*` | Runs the backtest on QC; reads results/charts/orders/insights. |
| **Risk / Bias Auditor** | `specialists/risk-auditor.agent.yaml` | `claude-opus-4-8` (fresh context) | read artifacts, bias-check; snooping **ledger** memory store in Phase 4 | Independent look-ahead/snooping audit; writes `audit.json`. |
| **Report agent** | `specialists/report.agent.yaml` | `claude-sonnet-4-6` | read artifacts, Skills (`pdf`/`docx`) | Produces the final report to `/mnt/session/outputs/`. |

## Why these model choices

- **Opus 4.8** for the coordinator and the correctness-critical authoring/audit agents (Modeling, Risk) —
  long-horizon agentic work + bug-finding. Run Modeling at `effort: high`/`xhigh`.
- **Sonnet 4.6** for the "judgment but high-volume" agents (Market, Feature, Report) and the Backtest agent,
  whose work is mechanical tool-driving (compile/backtest, read results) rather than open-ended authoring.
- **Haiku 4.5** for cheap retrieval/IO (Paper triage, Data pulls), escalating Paper to Opus for deep reads.
- The **Risk Auditor runs in a fresh thread** (its own context window) so its audit isn't anchored by the
  Modeling agent's rationalizations.

## Roster wiring (on the Research Manager)

```yaml
multiagent:
  type: coordinator
  agents:
    - { type: agent, id: ${PAPER_AGENT_ID} }
    - { type: agent, id: ${MARKET_AGENT_ID} }
    - { type: agent, id: ${DATA_AGENT_ID} }
    - { type: agent, id: ${FEATURE_AGENT_ID} }
    - { type: agent, id: ${MODELING_AGENT_ID} }
    - { type: agent, id: ${BACKTEST_AGENT_ID} }
    - { type: agent, id: ${RISK_AGENT_ID} }
    - { type: agent, id: ${REPORT_AGENT_ID} }
```

`make agents-apply` creates the specialists first, captures their IDs, then creates/updates the Manager
with the roster filled in. See [`agents/scripts/apply.sh`](../agents/scripts/apply.sh).

## Pipeline order (enforced by instructions + file bus)

The Research Manager's `system` prompt tells it the canonical order and the file contract:

```
Market/Paper     → returns cited ideas / hypotheses (idea-only; never directly backtested)
Data agent       → writes /workspace/features.parquet   (+ a data manifest with PIT timestamps)
Feature agent    → reads features.parquet, writes /workspace/features_enriched.parquet
Modeling agent   → reads contract, writes /workspace/algo.py  (must pass the validator)
Backtest agent   → compiles + backtests algo.py on QC, writes /workspace/results.json
Risk auditor     → reads algo.py + results.json + the data manifest, writes /workspace/audit.json
Report agent     → reads everything, writes /mnt/session/outputs/report.pdf
```

Because delegation is one level, the Manager re-delegates after each artifact appears, rather than the
agents calling each other.
