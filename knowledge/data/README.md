# knowledge/data/ — curated SSRN manifests

This directory holds **curated, hand-authored** inputs for the SSRN ingestion job. The whole `data/`
tree is gitignored (real corpora / dumps never get committed) **except** the tracked example manifest
and this README.

## What lives here

| File | Tracked? | Purpose |
|---|---|---|
| `ssrn_manifest.example.jsonl` | yes | 5 realistic sample rows you can copy from |
| `ssrn_manifest.jsonl` (your file) | no | your real curated manifest — kept local |
| extracted text / PDFs | no | never committed |

## SSRN is a curated manifest, not a scraper

SSRN access controls vary per paper and SSRN is **not** market data. The ingestion job therefore reads
**only** the papers you explicitly list in a local JSONL manifest. It never crawls or mass-downloads
SSRN, and it never downloads PDFs — `local_pdf_path` reads files already on disk. You are the curator:
you decide which papers are appropriate to ingest and you confirm redistribution rights.

## Manifest format (one JSON object per line)

Minimum for a row to be ingested: a `title`, a `url` (or `source`), and at least one of
`abstract` / `text` / `local_pdf_path`. Rows missing any of these are skipped with a warning — they do
not crash the job.

```json
{"title": "Time Series Momentum", "authors": ["Moskowitz", "Ooi", "Pedersen"], "year": 2012,
 "abstract": "We document significant time series momentum ...",
 "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463", "ssrn_id": "2089463",
 "doi": "10.1016/j.jfineco.2011.11.003", "citation": "Moskowitz et al. (2012), SSRN 2089463",
 "license": "abstract under fair use", "rights_checked": true,
 "strategy_family": "momentum", "asset_class": "multi-asset", "signal_type": "time-series",
 "data_needed": ["futures front-month prices", "12m lookback"],
 "tags": ["momentum", "trend-following"], "notes": "scale to constant ex-ante vol; rebalance monthly"}
```

### Fields

| Field | Type | Notes |
|---|---|---|
| `title` | str | **required** — chunk header + citation fallback |
| `url` / `source` | str | **required** — canonical SSRN abstract URL |
| `abstract` / `text` / `local_pdf_path` | str | **one required** — `text` wins over `abstract`; PDF used only if both empty |
| `authors` | list[str] or str | stored in metadata |
| `year` | int | citation + metadata |
| `citation` | str | defaults to `"<title> (<year>), SSRN"` |
| `tags` | list[str] | `"ssrn"` is always added |
| `ssrn_id`, `doi` | str | identifiers (metadata) |
| `license` | str | usage terms you verified |
| `rights_checked` | bool | you confirmed redistribution rights for the ingested text |
| `strategy_family` | str | e.g. `momentum`, `stat-arb`, `factor`, `volatility`, `validation` — also a tag |
| `asset_class` | str | e.g. `equities`, `futures`, `options`, `multi-asset` — also a tag |
| `signal_type` | str | e.g. `cross-sectional`, `time-series`, `event` — also a tag |
| `data_needed` | list[str] or str | what's required to test the idea |
| `notes` | str | hypothesis framing for the Paper Agent |
| `local_pdf_path` | str | LOCAL pdf; relative paths resolve against the manifest's directory |

`strategy_family`, `asset_class`, and `signal_type` are copied into both `metadata` and `tags` so the
Paper Agent can filter cheaply via the tag index.

## Running it

```bash
cd knowledge
export SSRN_PAPERS_JSONL=data/ssrn_manifest.example.jsonl

# Dry run: chunk only, write a JSONL snapshot, no DB writes
uv run python -m ingestion.run_all --jobs ssrn --dry-run --jsonl-dir out

# Real ingest (upsert into pgvector; requires the DB env, see ../../.env.example)
uv run python -m ingestion.run_all --jobs ssrn
```

Local PDF extraction needs a parser: `uv pip install pypdf` (or `pymupdf`). Without one, rows that rely
solely on `local_pdf_path` are skipped with a warning.

Re-running is safe: every chunk carries a `content_hash` (over provider + source + citation + text) and
the upsert uses `ON CONFLICT (content_hash) DO NOTHING`, so duplicates are not re-inserted.
