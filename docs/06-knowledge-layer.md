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
  (pgvector) — columns: `id, corpus, source, citation, tags[], chunk_text, embedding vector(N),
  metadata, content_hash`. A unique index on `content_hash` (provider + source + citation + chunk text)
  makes upserts idempotent (`ON CONFLICT DO NOTHING`), so re-running a job never duplicates rows.

## SSRN — curated manifest, not a scraper

SSRN is **idea/citation grounding** for the Paper Agent, **not** market data and **not** scraped.
QuantConnect remains the backtest/data backbone. The `ssrn` job ingests only the papers a curator
lists in a local JSONL manifest (`SSRN_PAPERS_JSONL`); see
[`knowledge/data/README.md`](../knowledge/data/README.md). Each row carries quant metadata
(`strategy_family`, `asset_class`, `signal_type`, `data_needed`, `authors`, `year`, `ssrn_id`, `doi`,
`license`, `rights_checked`, `notes`) — stored in `metadata` and, for the classification fields, mirrored
into `tags` so the Paper Agent can filter `corpus="papers"` by strategy type, asset class, and signal
type. Optional `local_pdf_path` extracts text from a **local** PDF (`pypdf`/`pymupdf`) — never a download.
Rows missing a title, url/source, or any body are skipped with a warning rather than crashing the job.
The Paper Agent must use these chunks to form and cite hypotheses only, then validate via QC backtests.

## Persistent state (Managed Agents memory stores, not the vector DB)

Two **memory stores** (docs/02) hold *learned* state, separate from the *reference* corpus:

- **Lessons library** — "approach X overfit on regime Y; prefer Z" (written by the Risk auditor + Manager).
- **Data-snooping ledger** — every variant + every `create_optimization` run, for the deflated-Sharpe
  computation (docs/08).

The vector DB is read-mostly reference; the memory stores are read-write running state.
