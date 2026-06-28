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

## SSRN: curated manifest, not a scraper

SSRN is **research grounding** (idea/citation material for the Paper Agent), **not** market data, and is
never scraped. The `ssrn` job ingests **only** the papers a curator explicitly lists in a local JSONL
manifest (`SSRN_PAPERS_JSONL`). QuantConnect stays the backtest/data backbone; SSRN chunks just give the
Paper Agent testable hypotheses with citations. See [`data/README.md`](data/README.md) for the full
manifest field reference and [`data/ssrn_manifest.example.jsonl`](data/ssrn_manifest.example.jsonl) for
5 ready-to-copy sample rows (momentum, pairs/stat-arb, factor, volatility, backtest-overfitting).

```bash
cd knowledge
export SSRN_PAPERS_JSONL=data/ssrn_manifest.example.jsonl

# Dry run — chunk + snapshot to JSONL, no DB writes:
uv run python -m ingestion.run_all --jobs ssrn --dry-run --jsonl-dir out
# Real ingest — upsert into pgvector:
uv run python -m ingestion.run_all --jobs ssrn
```

- **Local PDFs only.** If a row sets `local_pdf_path` and has empty `text`, text is extracted from that
  local file via `pypdf` (or `pymupdf`). PDFs are never downloaded from SSRN.
- **Validation.** A row missing `title`, `url`/`source`, or any body (`abstract`/`text`/`local_pdf_path`)
  is skipped with a warning; one bad row never crashes the job.
- **Dedup / idempotency.** Each chunk has a `content_hash` (provider + source + citation + text); the
  upsert is `ON CONFLICT (content_hash) DO NOTHING`, so re-running does not create duplicate rows.
- **Rich metadata.** `provider="ssrn"` plus `authors, year, ssrn_id, doi, license, rights_checked,
  strategy_family, asset_class, signal_type, data_needed, notes`. The classification fields are also
  tags, so the Paper Agent can filter `corpus="papers"` by strategy type, asset class, and signal type.

> Paper Agent contract: treat SSRN chunks as **idea/citation grounding only** — to form and cite
> hypotheses — never as a price/return source. Validate every hypothesis with a QuantConnect backtest.

## Pipeline (docs/06)

```
source → fetch → chunk → embed → upsert(vectorDB, {text, source, citation, corpus, tags})
```

- **Embedding model**: frozen to `intfloat/e5-small-v2` at 384 dimensions (docs/14 D11) — re-embedding a
  corpus is expensive. The local hash embedder is only a deterministic fallback for offline tests.
- **Chunking**: section-aware for papers (keep equations + context together); cell-level for notebooks.
- **Schema**: `schema/vectordb_schema.sql` (pgvector).
- **Licensing**: confirm QC repo terms before redistributing ingested Strategy Library text (docs/14 O7).

The jobs support `--dry-run` for local verification without network/database access.
