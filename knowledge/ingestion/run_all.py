"""Run ingestion jobs into the vector DB. `uv run python -m ingestion.run_all` (or `make ingest`).

Each job module exposes a uniform `collect_chunks(*, limit=None) -> list[KnowledgeChunk]` that resolves
its own source (local dir, manifest, or API) and degrades gracefully — a missing local repo or an
unreachable API prints a clear message and yields 0 chunks instead of crashing the pipeline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import arxiv, quantresearch_repo, ssrn, strategy_library
from .common import KnowledgeChunk, dedupe_chunks, write_jsonl

JOBS = {
    "arxiv": arxiv,
    "ssrn": ssrn,
    "quantresearch_repo": quantresearch_repo,
    "strategy_library": strategy_library,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", default=",".join(JOBS), help="Comma-separated job names.")
    parser.add_argument("--limit", type=int, default=None, help="Optional chunk/input limit per job.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch/chunk only; do not upsert.")
    parser.add_argument("--jsonl-dir", type=Path, default=None, help="Write chunks as JSONL snapshots.")
    args = parser.parse_args()

    selected = [name.strip() for name in args.jobs.split(",") if name.strip()]
    for name in selected:
        if name not in JOBS:
            raise SystemExit(f"Unknown ingestion job: {name} (known: {', '.join(JOBS)})")

    total = 0
    for name in selected:
        count = _run_job(name, args.limit, dry_run=args.dry_run, jsonl_dir=args.jsonl_dir)
        total += count
        print(f"{name}: {count} chunks")
    print(f"total: {total} chunks")


def _run_job(name: str, limit: int | None, *, dry_run: bool, jsonl_dir: Path | None) -> int:
    try:
        chunks = dedupe_chunks(_chunks_for_job(name, limit))
    except Exception as exc:  # isolate a failing job so the rest of the pipeline still runs
        print(f"[{name}] ERROR: {exc}; skipping job", file=sys.stderr)
        return 0

    if jsonl_dir:
        write_jsonl(chunks, jsonl_dir / f"{name}.jsonl")
    if dry_run:
        return len(chunks)

    from .common import upsert_chunks

    return upsert_chunks(chunks)


def _chunks_for_job(name: str, limit: int | None) -> list[KnowledgeChunk]:
    return JOBS[name].collect_chunks(limit=limit)


if __name__ == "__main__":
    main()
