# 06 — Knowledge layer

## One tool: `search_knowledge`

A single MCP tool over a **self-hosted vector DB** (pgvector or Qdrant) is the agents' window into the
"expertise" corpus. Lives in [`mcp/knowledge/`](../mcp/knowledge/). Bound to the Paper, Feature, and
Modeling agents.

```
search_knowledge(query, filters?, k?) -> [{text, source, citation, score, metadata}]
```

`filters` lets an agent scope by corpus (`papers` | `repo` | `strategy_library` | `contract`) or by tag
(e.g. `mean-reversion`, `pairs-trading`, `regime`). Always return a **citation** so the provenance view
(docs/09) can attribute a design to its sources.

## Corpora (fed by ingestion jobs in [`knowledge/`](../knowledge/))

| Corpus | Source | Job | Purpose |
|---|---|---|---|
| **papers** | SSRN papers + arXiv q-fin preprints | `ingestion/ssrn.py`, `ingestion/arxiv.py` | testable hypotheses |
| **repo** | `letianzj/QuantResearch` (27+ notebooks: Kalman/pairs, cointegration stat-arb, momentum/mean-reversion, GARCH/ARIMA, HMM regime, Fama-French, RL portfolio/option pricing, VaR) | `ingestion/quantresearch_repo.py` | canonical code patterns to ground/iterate algos |
| **strategy_library** | QC `Tutorials/04 Strategy Library` (1000+ documented strategies) | `ingestion/strategy_library.py` | grounded, QC-idiomatic strategy templates |
| **contract** | the authoring contract + lessons-learned | (loaded from [`contract/`](../contract/)) | so the Modeling agent can retrieve the rules it must follow |

## Pipeline

```
source → fetch → chunk → embed → upsert(vectorDB, {text, source, citation, corpus, tags})
```

- **Embeddings:** frozen to `intfloat/e5-small-v2` (384d; docs/14 D11). A deterministic hash embedder is
  available only for offline tests/dry-runs; production corpora should use the frozen local model.
- **Chunking:** semantic/section-aware for papers (keep equations + the surrounding paragraph together);
  cell-level for notebooks (so a retrieved chunk is a runnable pattern).
- **Schema:** see [`knowledge/schema/vectordb_schema.sql`](../knowledge/schema/vectordb_schema.sql)
  (pgvector) — columns: `id, corpus, source, citation, tags[], chunk_text, embedding vector(N)`.

## Persistent state (Managed Agents memory stores, not the vector DB)

Two **memory stores** (docs/02) hold *learned* state, separate from the *reference* corpus:

- **Lessons library** — "approach X overfit on regime Y; prefer Z" (written by the Risk auditor + Manager).
- **Data-snooping ledger** — every variant + every `create_optimization` run, for the deflated-Sharpe
  computation (docs/08).

The vector DB is read-mostly reference; the memory stores are read-write running state.
