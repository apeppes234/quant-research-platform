"""Tests for the arXiv ingestion job (mocked Atom feed; no network)."""

from __future__ import annotations

from ingestion import arxiv

# A trimmed but realistic arXiv Atom response with two entries (one malformed-ish).
SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.01234v1</id>
    <title>Time Series Momentum in Commodity Futures</title>
    <summary>We study time series momentum and trend following across commodity futures and find
    persistent volatility-scaled returns.</summary>
    <published>2024-01-03T10:00:00Z</published>
    <updated>2024-01-05T10:00:00Z</updated>
    <author><name>Jane Q. Researcher</name></author>
    <author><name>John Coauthor</name></author>
    <category term="q-fin.PM"/>
    <category term="q-fin.TR"/>
    <link href="http://arxiv.org/abs/2401.01234v1" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2401.01234v1" rel="related" type="application/pdf"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.05678v2</id>
    <title>Deep Learning for Options Pricing</title>
    <summary>A neural network approach to option pricing and implied volatility surfaces.</summary>
    <published>2024-01-10T10:00:00Z</published>
    <author><name>Solo Author</name></author>
    <category term="q-fin.CP"/>
  </entry>
</feed>"""


def _papers():
    import xml.etree.ElementTree as ET

    root = ET.fromstring(SAMPLE_ATOM)
    return [arxiv._parse_entry(e) for e in root.findall(f"{arxiv.ATOM}entry")]


def test_parse_entry_extracts_fields():
    papers = _papers()
    p0 = papers[0]
    assert p0["title"] == "Time Series Momentum in Commodity Futures"
    assert p0["authors"] == ["Jane Q. Researcher", "John Coauthor"]
    assert p0["arxiv_id"] == "2401.01234v1"
    assert p0["categories"] == ["q-fin.PM", "q-fin.TR"]
    assert p0["pdf_url"] == "http://arxiv.org/pdf/2401.01234v1"
    assert p0["source_url"] == "http://arxiv.org/abs/2401.01234v1"
    assert p0["updated"] == "2024-01-05T10:00:00Z"


def test_pdf_url_synthesized_when_missing():
    # second entry has no pdf link; build a canonical one from the id
    p1 = _papers()[1]
    assert p1["pdf_url"] == "https://arxiv.org/pdf/2401.05678v2"


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
    assert meta["pdf_url"] == "http://arxiv.org/pdf/2401.01234v1"
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
    import urllib.error

    def boom(*a, **k):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(arxiv, "fetch", boom)
    assert arxiv.collect_chunks(limit=5) == []
