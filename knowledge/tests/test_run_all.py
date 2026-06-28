"""Integration tests for the run_all dispatcher: dry-run JSONL, dedup, error isolation."""

from __future__ import annotations

import json
from pathlib import Path

from ingestion import run_all
from ingestion.common import KnowledgeChunk


def _chunk(text: str, provider: str = "test") -> KnowledgeChunk:
    return KnowledgeChunk(
        corpus="repo", source="s", citation="c", text=text, tags=["t"], metadata={"provider": provider}
    )


def test_dry_run_writes_jsonl(tmp_path, monkeypatch):
    sample = [_chunk("alpha body"), _chunk("beta body")]
    monkeypatch.setattr(run_all.quantresearch_repo, "collect_chunks", lambda **k: list(sample))

    count = run_all._run_job("quantresearch_repo", None, dry_run=True, jsonl_dir=tmp_path)
    assert count == 2

    out = (tmp_path / "quantresearch_repo.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(out) == 2
    row = json.loads(out[0])
    assert row["corpus"] == "repo"
    assert "content_hash" in row


def test_run_job_dedupes_chunks(tmp_path, monkeypatch):
    dup = _chunk("same body")
    monkeypatch.setattr(run_all.arxiv, "collect_chunks", lambda **k: [dup, dup, _chunk("other")])
    count = run_all._run_job("arxiv", None, dry_run=True, jsonl_dir=None)
    assert count == 2  # the duplicate collapses


def test_failing_job_is_isolated(monkeypatch, capsys):
    def boom(**k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(run_all.strategy_library, "collect_chunks", boom)
    count = run_all._run_job("strategy_library", None, dry_run=True, jsonl_dir=None)
    assert count == 0
    assert "kaboom" in capsys.readouterr().err


def test_all_jobs_expose_collect_chunks():
    for module in run_all.JOBS.values():
        assert hasattr(module, "collect_chunks")
