# Quant Research Platform

Quant Research Platform is a Claude-powered research workbench built around **QuantConnect**. QuantConnect
is the execution and backtesting backbone: agents create QuantConnect projects, write LEAN algorithms,
compile them, run cloud backtests, and read the resulting charts, orders, insights, and metrics back into
the app.

The second core idea is observability. When the system delegates work, runs a QuantConnect backtest, writes
an artifact, grades a strategy, or asks for human approval, that event appears on the canvas.

This is not a trading bot. There is no brokerage integration and no live trading path. The QuantConnect
tools are used for project/file/compile/backtest workflows only; live-trading tools are intentionally left
out of the allowlist.

## What This Is

You chat with a Research Manager agent. The Manager coordinates a team of specialists that move a strategy
from idea to report:

1. find grounded ideas from papers, notebooks, market context, and strategy references;
2. pull point-in-time data and record the as-of timestamps;
3. build features and author a QuantConnect algorithm under a strict contract;
4. validate, compile, and backtest the algorithm;
5. audit the result for look-ahead bias and data snooping;
6. iterate against a five-gate anti-overfit rubric;
7. produce a PDF report that says what worked, what failed, and how many variants were tried.

The UI is a live projection of the Managed Agents event stream. The graph nodes are agent threads, animated
edges are delegation/result messages, and artifact chips are files moving across the shared session
filesystem.

## QuantConnect, Data, And LLM Grounding

QuantConnect is not an optional plugin here; it is the platform the research loop is centered on.

- **Backtest engine:** QuantConnect LEAN runs the algorithms in the cloud.
- **Market and fundamental data:** the primary backtest data comes from QuantConnect subscriptions,
  history APIs, and datasets, including point-in-time and survivorship-bias-aware data where QC provides it.
- **Research workflow:** the Data and Feature agents use QuantConnect-style research patterns, then the
  Modeling and Backtest agents turn that work into a QuantConnect project.
- **Tool access:** the system talks to QuantConnect through the official `quantconnect/mcp-server` image,
  fronted by a bearer-auth proxy. The allowlist includes project, file, compile, backtest, read-results,
  and QC AI helper tools. Live-trading tools stay disabled.

Other data sources are supporting inputs, not replacements for QuantConnect:

| Source | Used for | Guardrail |
|---|---|---|
| QuantConnect | prices, fundamentals, datasets, project compile/backtest/results | core backtest data path |
| FRED / ALFRED | macro features and vintage-aware economic data | as-of timestamps in `data_manifest.json` |
| EDGAR | filings filtered by filing date | no future filing leakage |
| GDELT | news/event context | recorded as external feature provenance |
| arXiv / SSRN / reference repos | research ideas and citations | grounding only; not raw backtest data |
| QC Strategy Library | QC-idiomatic strategy examples | retrieved as design patterns with citations |

The LLM is **not fine-tuned by this repo** on private QuantConnect data or the local knowledge base. Claude
brings its base model capabilities, and this platform gives it runtime context through:

- the agent system prompts and fixed role boundaries;
- the strategy authoring contract and AST validator;
- `search_knowledge`, a vector search MCP over papers, notebooks, the QC Strategy Library, and contract
  material;
- live tool results from QuantConnect and the PIT data-source MCPs;
- Managed Agents memory stores for lessons learned and the data-snooping ledger.

In other words, the agents do not simply "remember" what to trade. They retrieve cited research, write a
contract-constrained QuantConnect algorithm, validate it, compile it, backtest it on QC, and then audit the
result.

## How The Agents Work Together

Anthropic Managed Agents has an important constraint: delegation is one level deep. That means the Research
Manager is the only coordinator. Specialists do not call each other. They write files, the Manager watches
for those files, and then the Manager delegates the next step.

The file bus is the handoff contract:

```text
Market/Paper  -> cited ideas and hypotheses
Data          -> /workspace/features.parquet + /workspace/data_manifest.json
Feature       -> /workspace/features_enriched.parquet
Modeling      -> /workspace/algo.py
Backtest      -> /workspace/results.json
Risk          -> /workspace/audit.json
Report        -> /mnt/session/outputs/report.pdf
```

The team:

| Agent | Job |
|---|---|
| Research Manager | Talks to the user, owns the run order, delegates to specialists, and drives the iteration loop. |
| Market | Generates market ideas and current-context leads. Web tools are allowed here because this is idea-only work. |
| Paper | Turns papers and reference material into testable hypotheses with citations. |
| Data | Pulls point-in-time datasets and writes a data manifest with as-of timestamps. |
| Feature | Builds and checks feature sets before anything reaches the model/backtest path. |
| Modeling | Writes `algo.py` under the authoring contract and runs the validator before compile. |
| Backtest | Uses QuantConnect MCP tools to create projects, compile, run backtests, and read results. |
| Risk | Runs in a fresh context to audit look-ahead, overfit, and snooping risk. |
| Report | Writes the final PDF from results, audit findings, provenance, and ledger state. |

The hard rule is still: constrain -> validate -> run. Natural language never goes straight into the
backtest engine. Strategy code must pass the contract validator first.

## System Shape

```text
User
  |
  v
Research Manager  -- one-level delegation -->  specialist agents
  |                                            |
  |                                            v
  |                                  shared session filesystem
  |                                            |
  v                                            v
Managed Agents SSE stream              algo.py / results.json / audit.json / report.pdf
  |
  v
FastAPI orchestrator  -- websocket -->  React + React Flow frontend
```

What runs where:

| Area | Runs on | Notes |
|---|---|---|
| Agent loop, coordinator, subagent threads, memory stores, session filesystem, files API | Anthropic Managed Agents | Created from `agents/*.yaml` with the `ant` CLI. |
| Backtests | QuantConnect cloud | Reached through the official self-hosted `quantconnect/mcp-server` image. |
| Orchestrator | Your machine or Docker | FastAPI service that creates sessions, consumes SSE, normalizes events, and relays websockets. |
| Frontend | Your machine or Docker | Vite/React/React Flow UI with shadcn dark-mode components. |
| MCP services | Your machine or Docker, exposed by HTTPS tunnel in dev | Knowledge search, QC proxy, FRED, EDGAR, GDELT, arXiv. |
| Vector DB and ingestion | Your machine or Docker | pgvector by default, embedding model pinned in docs/14. |

## Start Guide

### 1. Prerequisites

Install:

- Docker and Docker Compose
- Node 20+
- Python 3.11+
- `uv`
- the Anthropic `ant` CLI
- an Anthropic API key with Managed Agents access
- QuantConnect user ID and API token
- a public HTTPS tunnel for MCP endpoints during local development

### 2. Create your environment file

```bash
cp .env.example .env
```

Fill in at least:

```text
ANTHROPIC_API_KEY=
QUANTCONNECT_USER_ID=
QUANTCONNECT_API_TOKEN=
QC_MCP_INBOUND_BEARER=
KNOWLEDGE_MCP_INBOUND_BEARER=
FRED_MCP_INBOUND_BEARER=
EDGAR_MCP_INBOUND_BEARER=
GDELT_MCP_INBOUND_BEARER=
ARXIV_MCP_INBOUND_BEARER=
MCP_KNOWLEDGE_URL=
MCP_QUANTCONNECT_URL=
MCP_FRED_URL=
MCP_EDGAR_URL=
MCP_GDELT_URL=
MCP_ARXIV_URL=
```

Hosted Managed Agents must be able to reach MCP servers at public HTTPS URLs. Local `localhost` MCP URLs
will work for your browser, but not for the hosted agent containers.

### 3. Apply the agent control plane

This creates or updates the cloud environment, the eight specialists, and the Research Manager roster.
The script writes the resulting IDs back into `.env`.

```bash
make agents-diff
make agents-apply
```

If you only want to see the rendered YAML without changing anything, stop after `make agents-diff`.

### 4. Start the local data plane

Docker path:

```bash
make up
```

Local-dev path, in two terminals:

```bash
cd orchestrator && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open:

```text
http://localhost:5173
```

### 5. Ingest knowledge

The Modeling/Paper/Feature agents are meant to ground their work through `search_knowledge`, not guess from
memory. Apply the vector schema and run ingestion before expecting high-quality strategy design.

```bash
cd knowledge
uv sync
uv run python -m ingestion.run_all
```

The ingestion jobs cover papers, reference notebooks, and the QuantConnect strategy library. Check licensing
before redistributing any ingested corpus.

### 6. Run a first smoke test

With agents applied, MCP endpoints reachable, and the orchestrator/frontend running, send a request like:

```text
Backtest this starter strategy against the five-gate rubric.
```

You should see:

- the Research Manager node appear;
- delegation edges to specialists;
- artifact chips for `algo.py`, `results.json`, `audit.json`, and eventually `report.pdf`;
- backtest metrics and charts in the results panel;
- rubric criteria flipping as the iteration loop evaluates the run;
- a downloadable report when the Report agent publishes it.

## Common Commands

```bash
make help                 # list make targets
make agents-diff          # render agent/environment changes without applying
make agents-apply         # apply Managed Agents definitions and capture IDs
make up                   # start Docker services
make down                 # stop Docker services
make logs                 # tail Docker logs
make orchestrator         # run FastAPI locally
make frontend             # run Vite locally
make contract-validate    # validate the starter QuantConnect algorithm
make ingest               # run all knowledge ingestion jobs
make test                 # run the local test suite / smoke checks
```

## Current Status

The repository now contains the full application scaffold and local implementation surface through the
"full loop + polish" phase:

- Managed Agent YAMLs and apply script
- FastAPI orchestrator and event normalization
- React Flow/shadcn frontend
- QuantConnect MCP proxy setup
- strategy authoring contract and validator
- knowledge ingestion jobs and search MCP
- PIT data-source MCP wrappers
- iteration rubric, bias ledger, provenance, steering, and report download UI

A real end-to-end run still depends on live external setup: Managed Agents access, applied agent IDs,
reachable HTTPS MCP URLs, inbound bearer vaults, QuantConnect credentials, and a populated knowledge store.

## Where To Read Next

- [`docs/00-overview.md`](docs/00-overview.md) for the project philosophy
- [`docs/01-architecture.md`](docs/01-architecture.md) for the system map
- [`docs/02-managed-agents-platform.md`](docs/02-managed-agents-platform.md) for Managed Agents contracts
- [`docs/03-agent-topology.md`](docs/03-agent-topology.md) for the agent roster and file bus
- [`docs/04-quantconnect.md`](docs/04-quantconnect.md) for the QuantConnect MCP workflow
- [`docs/07-iteration-rubric.md`](docs/07-iteration-rubric.md) for the five-gate loop
- [`docs/08-antibias-guardrails.md`](docs/08-antibias-guardrails.md) for the risk and snooping machinery
- [`docs/10-orchestrator.md`](docs/10-orchestrator.md) for the SSE/websocket reliability patterns
- [`docs/14-decisions.md`](docs/14-decisions.md) for the decisions already made
