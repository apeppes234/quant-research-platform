"""Run all ingestion jobs into the vector DB. `uv run python -m ingestion.run_all` (or `make ingest`).

Each job: fetch → chunk → embed → upsert (docs/06). Embedding model is frozen (docs/14 O2). STATUS: scaffold.
"""
# from . import ssrn, arxiv, quantresearch_repo, strategy_library


def main() -> None:
    # for job in (ssrn, arxiv, quantresearch_repo, strategy_library):
    #     job.ingest()
    raise NotImplementedError("scaffold — wire the four ingestion jobs")


if __name__ == "__main__":
    main()
