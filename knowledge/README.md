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

Each job is one of three kinds: **automated** (arXiv hits a public API), **local reference** (the
QuantResearch repo and QC Strategy Library read a directory you clone), or **curated** (SSRN reads a
manifest you hand-author). All four feed the same `knowledge_chunks` table and share consistent metadata
(`provider`, `title`, `citation`, `source_url`/`source_path`, `source_type`, `tags`, …). None of them is
market data — QuantConnect remains the compile/backtest/data system; these corpora are grounding only.

## Common flags (`run_all`)

```bash
cd knowledge
# pick jobs individually or together:
uv run python -m ingestion.run_all --jobs arxiv
uv run python -m ingestion.run_all --jobs arxiv,quantresearch_repo,strategy_library

# --dry-run: chunk only, no DB writes.  --jsonl-dir: snapshot chunks to <dir>/<job>.jsonl.  --limit N: cap per job.
uv run python -m ingestion.run_all --jobs arxiv,quantresearch_repo,strategy_library --dry-run --jsonl-dir out
```

A missing local repo or an unreachable API prints a clear setup/skip message and yields 0 chunks — it
never crashes the rest of the pipeline. Re-running is safe: every chunk carries a `content_hash`
(`provider + source + citation + chunk_text`) and the upsert is `ON CONFLICT (content_hash) DO NOTHING`.

## arXiv — automated q-fin feed

Hits arXiv's keyless Atom API (default `cat:q-fin.*`). Pulls title, abstract, authors, published/updated
dates, arXiv id, categories, abstract URL, and PDF URL into `corpus="papers"` with `provider="arxiv"`.
Topic tags (`momentum`, `volatility`, `factor`, `options`, `machine-learning`, `mean-reversion`, …) are
inferred from the title + abstract. Abstract-only ingest is the MVP — PDFs are not downloaded.

```bash
# default q-fin feed, 50 newest:
uv run python -m ingestion.run_all --jobs arxiv
# custom query/limit via the module API:
uv run python -c "from ingestion import arxiv; print(arxiv.ingest(query='cat:q-fin.PM', limit=20))"
```

## QuantResearch repo — local notebooks/code

Clone the repo yourself and point `QUANTRESEARCH_REPO_PATH` at it (the job never downloads). Ingests
`.ipynb` (chunked by cell — code cells stay code, markdown cells stay explanation), `.md`, and `.py` into
`corpus="repo"` with `provider="quantresearch_repo"`. Tags inferred from path + text (`kalman-filter`,
`pairs-trading`, `cointegration`, `momentum`, `mean-reversion`, `garch`, `arima`, `hmm`, `regime`,
`fama-french`, `factor`, `reinforcement-learning`, `var`, `risk`).

```bash
git clone https://github.com/letianzj/QuantResearch ~/src/QuantResearch
export QUANTRESEARCH_REPO_PATH=~/src/QuantResearch
uv run python -m ingestion.run_all --jobs quantresearch_repo --dry-run --jsonl-dir out
```

## QuantConnect Strategy Library — local implementation patterns

Clone QuantConnect's Tutorials (or any folder of QC examples) and point `STRATEGY_LIBRARY_PATH` at the
strategy directory. Ingests `.md`, `.py`, `.cs`, `.ipynb`, `.txt` into `corpus="strategy_library"` with
`provider="quantconnect_strategy_library"`, recording strategy name, language, and inferred
`strategy_family`. Tags: `momentum`, `mean-reversion`, `pairs-trading`, `factor`, `options`, `futures`,
`crypto`, `universe-selection`, `risk-management`, `portfolio-construction`, `alpha-model`,
`execution-model`. Every chunk carries a `disclaimer` — these are **implementation patterns, not
profitable strategies**; profitability is only ever established by the backtest/risk workflow.

```bash
git clone https://github.com/QuantConnect/Tutorials ~/src/Tutorials
export STRATEGY_LIBRARY_PATH="$HOME/src/Tutorials/04 Strategy Library"   # or QUANTCONNECT_STRATEGY_LIBRARY_PATH
uv run python -m ingestion.run_all --jobs strategy_library --dry-run --jsonl-dir out
```

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
