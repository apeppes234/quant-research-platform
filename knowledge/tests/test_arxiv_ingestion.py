"""Tests for the arXiv ingestion job (uses the `arxiv` package; no network)."""

from __future__ import annotations

import datetime

import arxiv as arxiv_api

from ingestion import arxiv


def _result(
    *,
    entry_id: str,
    title: str,
    summary: str,
    authors: list[str],
    categories: list[str],
    pdf_url: str | None = None,
    published: datetime.datetime | None = None,
    updated: datetime.datetime | None = None,
) -> arxiv_api.Result:
    return arxiv_api.Result(
        entry_id=entry_id,
        title=title,
        summary=summary,
        authors=[arxiv_api.Result.Author(name) for name in authors],
        categories=categories,
        published=published or datetime.datetime(2024, 1, 3, 10, 0, 0),
        updated=updated or datetime.datetime(2024, 1, 5, 10, 0, 0),
    )


def _momentum_result() -> arxiv_api.Result:
    return _result(
        entry_id="http://arxiv.org/abs/2401.01234v1",
        title="Time Series Momentum in Commodity Futures",
        summary="We study time series momentum and trend following across commodity futures.",
        authors=["Jane Q. Researcher", "John Coauthor"],
        categories=["q-fin.PM", "q-fin.TR"],
    )


def _options_result() -> arxiv_api.Result:
    return _result(
        entry_id="http://arxiv.org/abs/2401.05678v2",
        title="Deep Learning for Options Pricing",
        summary="A neural network approach to option pricing and implied volatility surfaces.",
        authors=["Solo Author"],
        categories=["q-fin.CP"],
    )


# Plain dict rows (the shape build_chunks consumes) — no package needed.
def _papers() -> list[dict]:
    return [arxiv._result_to_dict(_momentum_result()), arxiv._result_to_dict(_options_result())]


def test_result_to_dict_extracts_fields():
    p0 = arxiv._result_to_dict(_momentum_result())
    assert p0["title"] == "Time Series Momentum in Commodity Futures"
    assert p0["authors"] == ["Jane Q. Researcher", "John Coauthor"]
    assert p0["arxiv_id"] == "2401.01234v1"
    assert p0["categories"] == ["q-fin.PM", "q-fin.TR"]
    assert p0["source_url"] == "http://arxiv.org/abs/2401.01234v1"
    assert str(p0["published"]).startswith("2024-01-03")
    assert str(p0["updated"]).startswith("2024-01-05")


def test_pdf_url_synthesized_when_missing():
    # arxiv.Result computes pdf_url from links; with none provided it falls back to None,
    # so _result_to_dict synthesizes the canonical pdf URL from the short id.
    p1 = arxiv._result_to_dict(_options_result())
    assert p1["pdf_url"] == "https://arxiv.org/pdf/2401.05678v2"


def test_fetch_maps_client_results(monkeypatch):
    results = [_momentum_result(), _options_result()]
    monkeypatch.setattr(arxiv_api.Client, "results", lambda self, search: iter(results))
    papers = arxiv.fetch(query="cat:q-fin.*", limit=5)
    assert [p["arxiv_id"] for p in papers] == ["2401.01234v1", "2401.05678v2"]


def test_build_chunks_corpus_and_provider():
    chunks = arxiv.build_chunks(_papers())
    assert chunks
    for chunk in chunks:
        assert chunk.corpus == "papers"
        assert chunk.metadata["provider"] == "arxiv"
        assert "arxiv" in chunk.tags and "q-fin" in chunk.tags


def test_topic_tags_inferred():
    chunks = arxiv.build_chunks(_papers())
    momentum = next(c for c in chunks if "Momentum" in str(c.metadata["title"]))
    assert "momentum" in momentum.tags
    options = next(c for c in chunks if "Options" in str(c.metadata["title"]))
    assert "options" in options.tags
    assert "machine-learning" in options.tags


def test_metadata_preserved():
    chunk = arxiv.build_chunks(_papers())[0]
    meta = chunk.metadata
    assert meta["arxiv_id"] == "2401.01234v1"
    assert meta["pdf_url"] == "https://arxiv.org/pdf/2401.01234v1"
    assert meta["source_url"] == "http://arxiv.org/abs/2401.01234v1"
    assert meta["categories"] == ["q-fin.PM", "q-fin.TR"]
    assert meta["source_type"] == "paper"
    assert "Researcher" in meta["citation"] and "arXiv:2401.01234v1" in meta["citation"]


def test_citation_handles_single_and_multi_author():
    papers = _papers()
    multi = arxiv._citation(papers[0]["authors"], "2024", papers[0]["title"], papers[0]["arxiv_id"])
    single = arxiv._citation(papers[1]["authors"], "2024", papers[1]["title"], papers[1]["arxiv_id"])
    assert "et al." in multi
    assert "et al." not in single and "Solo Author" in single


def test_collect_chunks_returns_empty_on_network_error(monkeypatch):
    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(arxiv, "fetch", boom)
    assert arxiv.collect_chunks(limit=5) == []
