"""Tests for the curated-manifest SSRN ingestion path (knowledge/ingestion/ssrn.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ingestion import ssrn
from ingestion.common import dedupe_chunks

EXAMPLE_MANIFEST = Path(__file__).resolve().parents[1] / "data" / "ssrn_manifest.example.jsonl"


def _write_manifest(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "manifest.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def test_example_manifest_loads_and_builds_chunks():
    rows = ssrn.load_manifest(EXAMPLE_MANIFEST)
    assert len(rows) == 5
    chunks = ssrn.build_chunks(rows, manifest_dir=EXAMPLE_MANIFEST.parent)
    assert chunks, "example manifest should produce chunks"


def test_load_manifest_skips_blank_lines(tmp_path):
    path = tmp_path / "m.jsonl"
    path.write_text(
        json.dumps({"title": "A", "url": "u", "abstract": "x"}) + "\n\n   \n",
        encoding="utf-8",
    )
    assert len(ssrn.load_manifest(path)) == 1


def test_corpus_is_papers_and_tags_include_ssrn():
    rows = [{"title": "Momentum", "url": "https://ssrn/x", "abstract": "momentum works", "tags": ["momentum"]}]
    chunks = ssrn.build_chunks(rows)
    assert chunks
    for chunk in chunks:
        assert chunk.corpus == "papers"
        assert "ssrn" in chunk.tags


def test_metadata_fields_preserved():
    row = {
        "title": "Vol Premium",
        "url": "https://ssrn/v",
        "abstract": "selling variance earns a premium",
        "authors": ["Jane Doe"],
        "year": 2009,
        "ssrn_id": "12345",
        "doi": "10.0/abc",
        "license": "fair use",
        "rights_checked": True,
        "strategy_family": "volatility",
        "asset_class": "options",
        "signal_type": "time-series",
        "data_needed": ["implied vol", "realized vol"],
        "notes": "harvest VRP",
    }
    chunk = ssrn.build_chunks([row])[0]
    meta = chunk.metadata
    assert meta["provider"] == "ssrn"
    assert meta["authors"] == ["Jane Doe"]
    assert meta["year"] == 2009
    assert meta["ssrn_id"] == "12345"
    assert meta["doi"] == "10.0/abc"
    assert meta["license"] == "fair use"
    assert meta["rights_checked"] is True
    assert meta["strategy_family"] == "volatility"
    assert meta["asset_class"] == "options"
    assert meta["signal_type"] == "time-series"
    assert meta["data_needed"] == ["implied vol", "realized vol"]
    assert meta["notes"] == "harvest VRP"
    # Classification fields are also exposed as tags for cheap filtering.
    assert "volatility" in chunk.tags
    assert "options" in chunk.tags
    assert "time-series" in chunk.tags


def test_citation_and_source_preserved():
    rows = [{"title": "Paper", "url": "https://ssrn/paper", "abstract": "body", "year": 2020}]
    chunk = ssrn.build_chunks(rows)[0]
    assert chunk.source == "https://ssrn/paper"
    assert "Paper" in chunk.citation and "SSRN" in chunk.citation

    explicit = [{"title": "P", "url": "u", "abstract": "b", "citation": "Custom Cite 2021"}]
    assert ssrn.build_chunks(explicit)[0].citation == "Custom Cite 2021"


@pytest.mark.parametrize(
    "row",
    [
        {"url": "u", "abstract": "x"},  # missing title
        {"title": "T", "abstract": "x"},  # missing url/source
        {"title": "T", "url": "u"},  # missing body
    ],
)
def test_bad_rows_are_skipped(row, capsys):
    chunks = ssrn.build_chunks([row])
    assert chunks == []
    assert "WARNING" in capsys.readouterr().err


def test_one_bad_row_does_not_drop_good_rows():
    rows = [
        {"title": "Good", "url": "https://ssrn/good", "abstract": "valid body"},
        {"abstract": "no title or url"},
    ]
    chunks = ssrn.build_chunks(rows)
    assert chunks
    assert all(c.corpus == "papers" for c in chunks)


def test_source_alias_satisfies_validation():
    rows = [{"title": "T", "source": "https://ssrn/s", "abstract": "body"}]
    chunks = ssrn.build_chunks(rows)
    assert chunks and chunks[0].source == "https://ssrn/s"


def test_duplicate_ingestion_is_deduplicated_in_memory():
    rows = [{"title": "Dup", "url": "https://ssrn/d", "abstract": "same content"}]
    first = ssrn.build_chunks(rows)
    # Re-running the same manifest yields identical content hashes...
    second = ssrn.build_chunks(rows)
    assert [c.content_hash for c in first] == [c.content_hash for c in second]
    # ...and de-duplicating the combined set collapses to the original chunk count.
    combined = dedupe_chunks([*first, *second])
    assert len(combined) == len(first)


def test_text_preferred_over_abstract():
    rows = [{"title": "T", "url": "u", "abstract": "short abstract", "text": "the full long text body"}]
    chunk = ssrn.build_chunks(rows)[0]
    assert "full long text body" in chunk.text
    assert "short abstract" not in chunk.text


def test_ingest_with_missing_manifest_returns_zero(tmp_path):
    assert ssrn.ingest(manifest=str(tmp_path / "nope.jsonl"), upsert=False) == 0


def test_ingest_dry_run_counts_chunks(tmp_path):
    path = _write_manifest(tmp_path, [{"title": "T", "url": "u", "abstract": "body text here"}])
    count = ssrn.ingest(manifest=str(path), upsert=False)
    assert count >= 1


def _minimal_pdf(text: str) -> bytes:
    """A tiny, valid single-page PDF with extractable text and correct xref offsets."""

    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, body)
    xref_pos = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref_pos)
    return out


def test_extract_pdf_text_reads_local_pdf(tmp_path):
    pytest.importorskip("pypdf")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(_minimal_pdf("Momentum strategy hypothesis"))
    assert "Momentum strategy hypothesis" in ssrn.extract_pdf_text(pdf)


def test_build_chunks_extracts_pdf_when_text_empty(tmp_path):
    pytest.importorskip("pypdf")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(_minimal_pdf("Pairs trading relative value"))
    rows = [{"title": "PDF Paper", "url": "https://ssrn/p", "local_pdf_path": str(pdf)}]
    chunk = ssrn.build_chunks(rows)[0]
    assert "Pairs trading relative value" in chunk.text


def test_extract_pdf_text_missing_file_returns_empty(tmp_path, capsys):
    assert ssrn.extract_pdf_text(tmp_path / "absent.pdf") == ""
    assert "WARNING" in capsys.readouterr().err


def test_local_pdf_used_when_text_empty(tmp_path, monkeypatch):
    """A row with local_pdf_path and no text should fall back to extracted PDF text."""

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr(ssrn, "extract_pdf_text", lambda path: "extracted pdf body about momentum")

    rows = [{"title": "PDF Paper", "url": "https://ssrn/p", "local_pdf_path": str(pdf)}]
    chunk = ssrn.build_chunks(rows)[0]
    assert "extracted pdf body about momentum" in chunk.text


def test_relative_pdf_path_resolved_against_manifest_dir(tmp_path, monkeypatch):
    (tmp_path / "paper.pdf").write_bytes(b"%PDF-1.4 fake")
    seen: dict[str, Path] = {}

    def fake_extract(path: Path) -> str:
        seen["path"] = path
        return "body from relative pdf"

    monkeypatch.setattr(ssrn, "extract_pdf_text", fake_extract)
    rows = [{"title": "Rel", "url": "u", "local_pdf_path": "paper.pdf"}]
    ssrn.build_chunks(rows, manifest_dir=tmp_path)
    assert seen["path"] == tmp_path / "paper.pdf"
