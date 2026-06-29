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

Current implementation note: the app can run a Claude/Managed Agents smoke test before QuantConnect is
connected. Blank MCP URLs are rendered as disabled placeholders when agents are applied. Chat, delegation,
the event stream, and the Research UI can be tested this way, but QuantConnect compile/backtest tools will
fail until you provide the QC MCP URL, bearer, and QC credentials, rerun `make agents-apply`, and start a
new session.

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
| Agent loop, coordinator, subagent threads, memory stores, session filesystem, files API | Anthropic Managed Agents | Created from `agents/*.yaml` with `make agents-apply`; uses the `ant` CLI when installed, otherwise the Anthropic Python SDK fallback. |
| Backtests | QuantConnect cloud | Reached through the official self-hosted `quantconnect/mcp-server` image. |
| Orchestrator | Your machine or Docker | FastAPI service that creates sessions, consumes SSE, normalizes events, and relays websockets. |
| Frontend | Your machine or Docker | Vite/React/React Flow UI with shadcn dark-mode components. |
| MCP services | Your machine or Docker, exposed by HTTPS tunnel in dev | Knowledge search, QC proxy, FRED, EDGAR, GDELT, arXiv. |
| Vector DB and ingestion | Your machine or Docker | pgvector by default, embedding model pinned in docs/14. |

## Start Guide

### 1. Prerequisites

Install:

- Node 20+
- Python 3.11+
- `uv`
- an Anthropic API key with Managed Agents access
- Docker and Docker Compose if you want to run MCP services locally
- a public HTTPS tunnel such as ngrok or cloudflared for any MCP endpoint the hosted agents must reach
- QuantConnect user ID and API token only when you are ready to run QC compile/backtest work

The Anthropic `ant` CLI is optional. `make agents-apply` uses `ant` when it is on `PATH`; otherwise it
falls back to the Anthropic Python SDK through `uv`.

### 2. Create `.env`

```bash
cp .env.example .env
```

For the first Claude/Managed Agents smoke test, fill in only:

```text
ANTHROPIC_API_KEY=sk-ant-...
```

Leave the generated IDs blank. `make agents-apply` writes `MANAGED_ENVIRONMENT_ID`,
`RESEARCH_MANAGER_AGENT_ID`, and all specialist `*_AGENT_ID` values back into `.env`.

Do not paste secrets into prompts or agent YAML. MCP credentials that hosted agents need at runtime are
attached through Anthropic vaults. The orchestrator creates those vaults automatically when both an
`MCP_*_URL` and the matching `*_MCP_INBOUND_BEARER` are present.

### 3. Apply the Managed Agents control plane

```bash
make agents-diff
make agents-apply
```

`make agents-diff` renders the YAML without changing anything. `make agents-apply` creates or replaces the
cloud environment, the eight specialists, and the Research Manager roster.

Blank MCP URLs are allowed. The apply script renders them as `https://disabled.invalid/...` placeholders so
you can bring up the app before every external service exists. If you later add or change an MCP URL, rerun
`make agents-apply` and start a fresh session; existing sessions keep the agent/tool definitions they were
created with.

### 4. Run the local app

Use two terminals for the most predictable local development path:

```bash
cd orchestrator
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The Vite dev server proxies `/api` and `/ws` to the orchestrator on port `8000`.

### 5. Smoke test the Claude session

With only `ANTHROPIC_API_KEY` and the generated agent IDs, you can test the Managed Agents connection and
UI event stream. Send a normal message such as:

```text
Say hello and tell me whether the research manager is online.
```

You should see a real session start, the Research Manager respond in chat, and websocket status move to
open. This does not require QuantConnect yet.

### 6. Enable research sources and PDF preview

The Research tab is populated from structured provenance events. It now supports three paths:

- `search_knowledge` results from the knowledge MCP;
- direct arXiv MCP results such as `arxiv_qfin_papers`;
- arXiv links or `arXiv:...` IDs mentioned in normal Paper Agent messages.

arXiv PDFs are opened through the same-origin backend proxy at `/api/pdfs/arxiv`, so the browser is not
embedding `arxiv.org` directly. Local PDFs can also be served through `/api/pdfs?path=...`, but only from
approved directories in `PDF_SERVE_ROOTS` or the default `knowledge/data` tree.

For structured knowledge search, configure and expose the knowledge/arXiv MCP wrappers:

```text
MCP_KNOWLEDGE_URL=https://.../mcp
KNOWLEDGE_MCP_INBOUND_BEARER=...
MCP_ARXIV_URL=https://...
ARXIV_MCP_INBOUND_BEARER=...
```

Then rerun:

```bash
make agents-apply
```

Run ingestion before expecting high-quality strategy design from `search_knowledge`:

```bash
cd knowledge
uv sync
uv run python -m ingestion.run_all
```

The ingestion jobs cover papers, reference notebooks, and the QuantConnect strategy library. Check licensing
before redistributing any ingested corpus.

### 7. Enable QuantConnect backtests

Leave QuantConnect blank until you are ready for compile/backtest work. When ready, fill in:

```text
QUANTCONNECT_USER_ID=...
QUANTCONNECT_API_TOKEN=...
QC_MCP_INBOUND_BEARER=...
MCP_QUANTCONNECT_URL=https://.../mcp
```

Run the official QuantConnect MCP behind the bearer proxy:

```bash
make mcp-quantconnect
```

Expose the proxy's local port `9002` through a public HTTPS tunnel and set `MCP_QUANTCONNECT_URL` to that
public URL, including the `/mcp` path. Rerun `make agents-apply`, restart the orchestrator if its env has
changed, and start a fresh UI session.

During a full run, QuantConnect begins at the Modeling Agent stage. That agent creates a QC project, writes
the algorithm files, compiles, and fixes warnings. The Backtest Agent then calls `create_backtest` and
reads back metrics, charts, orders, and insights. Live-trading tools are not enabled.

### 8. Run a full research loop

After Managed Agents, desired MCPs, knowledge ingestion, and optional QuantConnect are configured, send a
request like:

```text
Research a factor timing strategy conditioned on macro regimes.
```

You should see:

- the Research Manager node appear;
- delegation edges to specialists;
- Research sources and arXiv PDFs when papers are cited;
- artifact chips for `algo.py`, `results.json`, `audit.json`, and eventually `report.pdf`;
- backtest metrics and charts in the Results tab once QuantConnect is connected;
- rubric criteria flipping as the iteration loop evaluates the run;
- a downloadable report when the Report agent publishes it.

## Common Commands

```bash
make help                 # list make targets
make agents-diff          # render agent/environment changes without applying
make agents-apply         # apply Managed Agents definitions and capture IDs
make up                   # start Docker services; local-dev path above is simpler for first run
make down                 # stop Docker services
make logs                 # tail Docker logs
make orchestrator         # run FastAPI locally
make frontend             # run Vite locally
make contract-validate    # validate the starter QuantConnect algorithm
make ingest               # run all knowledge ingestion jobs
make test                 # best-effort local smoke checks; run package test commands directly for strict CI
```

## Current Status

Implemented and verified locally:

- Managed Agent YAMLs plus `make agents-apply`, with `ant` CLI or SDK fallback
- FastAPI orchestrator that creates sessions, attaches vaults/memory stores, consumes Managed Agents events,
  normalizes them, and relays them over websockets
- React/Vite UI with live chat, agent graph, team directory, steering controls, Research tab, Results tab,
  Insights tabs, report download, and confirmation UI for gated tools
- arXiv PDF preview through a same-origin proxy, including automatic Research sources from arXiv MCP
  results and arXiv links in agent messages
- QuantConnect MCP configuration and specialist allowlists for project/file/compile/backtest workflows
- strategy authoring contract and validator
- knowledge ingestion jobs and `search_knowledge` MCP
- PIT data-source MCP wrappers for FRED/ALFRED, EDGAR, GDELT, and arXiv
- regression tests for event normalization, PDF routing, contract validation, and metric helpers

Current external dependencies for a real full-loop backtest:

- Anthropic Managed Agents access and applied agent IDs
- public HTTPS MCP URLs for any tools the hosted agents should use
- inbound bearer values so the orchestrator can create Anthropic `static_bearer` vaults
- a populated knowledge store for high-quality `search_knowledge` grounding
- QuantConnect credentials plus the public QC MCP proxy URL for compile/backtest work

Without QuantConnect, the app can still run real Claude sessions, show delegation/chat events, and populate
Research sources from arXiv links or configured research MCPs. Backtest creation and QC result panels require
the QuantConnect MCP setup.

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
