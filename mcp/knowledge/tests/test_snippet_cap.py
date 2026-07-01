"""search_knowledge payload-cap tests (no DB, no network)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import search  # noqa: E402


def test_snippet_leaves_short_text_untouched():
    text = "a short chunk"
    snippet, full = search._snippet(text, "papers")
    assert snippet == text
    assert full is None


def test_snippet_truncates_long_text_and_reports_length():
    text = "word " * 2000  # ~10k chars, far above the default cap
    snippet, full = search._snippet(text, "papers")
    assert full == len(text)
    assert len(snippet) < len(text)
    assert snippet.endswith("…[truncated]")


def test_contract_corpus_gets_more_room_than_papers():
    text = "x" * 3000  # between the papers cap and the contract cap
    paper_snippet, paper_full = search._snippet(text, "papers")
    contract_snippet, contract_full = search._snippet(text, "contract")
    assert paper_full == len(text)  # truncated for papers
    assert contract_full is None  # fits under the contract cap
    assert len(contract_snippet) >= len(paper_snippet)


def test_bound_chunk_flags_truncation_in_metadata():
    row = {"text": "y" * 5000, "corpus": "papers", "metadata": {"citation": "X"}}
    bounded = search._bound_chunk(row)
    assert bounded["metadata"]["truncated"] is True
    assert bounded["metadata"]["full_length"] == 5000
    assert bounded["metadata"]["citation"] == "X"  # existing metadata preserved
    assert len(bounded["text"]) < 5000


def test_search_fallback_bounds_whole_file_contract_chunks():
    # The contract fallback reads entire files as single chunks; every returned
    # chunk must still respect the contract cap.
    rows = asyncio.run(search.search("contract rubric validator", corpus="contract", k=8))
    assert rows
    for row in rows:
        assert len(row["text"]) <= search._CONTRACT_SNIPPET_CHARS + len("\n…[truncated]")


def test_max_k_ceiling_is_enforced():
    rows = asyncio.run(search.search("contract", corpus="contract", k=999))
    assert len(rows) <= search._MAX_K
