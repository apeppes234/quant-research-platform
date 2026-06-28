"""Run ingestion jobs into the vector DB. `uv run python -m ingestion.run_all` (or `make ingest`)."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import arxiv, quantresearch_repo, ssrn, strategy_library
from .common import KnowledgeChunk, write_jsonl

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
    total = 0
    for name in selected:
        if name not in JOBS:
            raise SystemExit(f"Unknown ingestion job: {name}")
        count = _run_job(name, args.limit, dry_run=args.dry_run, jsonl_dir=args.jsonl_dir)
        total += count
        print(f"{name}: {count} chunks")
    print(f"total: {total} chunks")


def _run_job(name: str, limit: int | None, *, dry_run: bool, jsonl_dir: Path | None) -> int:
    module = JOBS[name]
    if jsonl_dir:
        chunks = _chunks_for_job(name, limit)
        write_jsonl(chunks, jsonl_dir / f"{name}.jsonl")
        if dry_run:
            return len(chunks)
        from .common import upsert_chunks

        return upsert_chunks(chunks)
    return module.ingest(limit=limit, upsert=not dry_run)


def _chunks_for_job(name: str, limit: int | None) -> list[KnowledgeChunk]:
    if name == "arxiv":
        return arxiv.build_chunks(arxiv.fetch(limit=limit or 50))
    if name == "ssrn":
        import os

        manifest = os.getenv("SSRN_PAPERS_JSONL", "")
        return ssrn.build_chunks(ssrn.load_manifest(Path(manifest))) if manifest else []
    if name == "quantresearch_repo":
        return quantresearch_repo.build_chunks(quantresearch_repo.source_root(), limit=limit)
    if name == "strategy_library":
        return strategy_library.build_chunks(strategy_library.source_root(), limit=limit)
    raise ValueError(name)


if __name__ == "__main__":
    main()
