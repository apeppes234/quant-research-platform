# knowledge/ — ingestion jobs feeding the vector DB

Populate the corpora that `search_knowledge` (mcp/knowledge) serves (docs/06). Read-mostly *reference*
data — distinct from the *running state* in Managed Agents memory stores (lessons + snooping ledger).

## Corpora & jobs

| Job | Source | Corpus tag |
|---|---|---|
| `ingestion/ssrn.py` | SSRN papers (PDFs/abstracts) | `papers` |
| `ingestion/arxiv.py` | arXiv q-fin preprints | `papers` |
| `ingestion/quantresearch_repo.py` | `letianzj/QuantResearch` notebooks (Kalman/pairs, cointegration, momentum/MR, GARCH/ARIMA, HMM regime, Fama-French, RL, VaR) | `repo` |
| `ingestion/strategy_library.py` | QuantConnect `Tutorials/04 Strategy Library` (1000+ documented strategies) | `strategy_library` |

Run all: `uv run python -m ingestion.run_all` (or `make ingest`).

## Pipeline (docs/06)

```
source → fetch → chunk → embed → upsert(vectorDB, {text, source, citation, corpus, tags})
```

- **Embedding model**: pick one and FREEZE it (docs/14 O2) — re-embedding a corpus is expensive.
- **Chunking**: section-aware for papers (keep equations + context together); cell-level for notebooks.
- **Schema**: `schema/vectordb_schema.sql` (pgvector).
- **Licensing**: confirm QC repo terms before redistributing ingested Strategy Library text (docs/14 O7).

STATUS: scaffold.
