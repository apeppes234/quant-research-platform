"""Ingest arXiv q-fin preprints -> corpus 'papers' via the official `arxiv` PyPI client. docs/06.

arXiv is the **automated** academic feed (contrast SSRN, which is curated/manual). The `arxiv` package
wraps arXiv's public, keyless API (paging, retries, rate-limit delay), so this module just maps its
``arxiv.Result`` objects into our ``KnowledgeChunk`` shape. Results are research grounding/citations for
the Paper Agent — not a price/return source; every hypothesis is validated later by a QC backtest.
"""

from __future__ import annotations

import sys

import arxiv as arxiv_api

from .common import KnowledgeChunk, chunk_text, infer_tags

# Canonical topic tag -> substrings that imply it (matched against title + abstract).
TOPIC_VOCAB: dict[str, tuple[str, ...]] = {
    "momentum": ("momentum", "trend follow", "time series momentum"),
    "mean-reversion": ("mean revers", "mean-revert", "contrarian"),
    "pairs-trading": ("pairs trad", "pair trad", "statistical arbitrage", "stat arb"),
    "cointegration": ("cointegrat",),
    "factor": ("factor model", "factor invest", "cross-section", "cross section", "fama"),
    "volatility": ("volatilit", "garch", "variance", "vix"),
    "options": ("option pricing", "implied vol", "derivative", "black-scholes", "black scholes"),
    "portfolio": ("portfolio", "asset allocation", "markowitz", "risk parity"),
    "microstructure": ("microstructure", "order book", "limit order", "high frequency", "high-frequency"),
    "machine-learning": ("machine learning", "deep learning", "neural network", "reinforcement learning", "lstm", "transformer"),
    "risk": ("value at risk", "var ", "drawdown", "tail risk", "expected shortfall"),
    "regime": ("regime", "hidden markov", "markov switch"),
}


def fetch(query: str = "cat:q-fin.*", *, limit: int = 50) -> list[dict[str, object]]:
    search = arxiv_api.Search(
        query=query,
        max_results=max(1, min(limit, 100)),
        sort_by=arxiv_api.SortCriterion.SubmittedDate,
        sort_order=arxiv_api.SortOrder.Descending,
    )
    papers: list[dict[str, object]] = []
    for result in arxiv_api.Client().results(search):
        try:
            papers.append(_result_to_dict(result))
        except Exception as exc:  # one malformed entry must not kill the batch
            _warn(f"skipping malformed entry ({exc})")
    return papers


def build_chunks(papers: list[dict[str, object]]) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for paper in papers:
        try:
            chunks.extend(_chunks_for_paper(paper))
        except Exception as exc:  # defensive: never let one paper abort the job
            _warn(f"skipping paper during chunking ({exc}): {paper.get('title')!r}")
    return chunks


def collect_chunks(*, query: str = "cat:q-fin.*", limit: int | None = None) -> list[KnowledgeChunk]:
    """Fetch + chunk, degrading to an empty list (with a warning) on network/API failure."""

    try:
        papers = fetch(query=query, limit=limit or 50)
    except (arxiv_api.ArxivError, OSError, TimeoutError) as exc:
        _warn(f"arXiv API unreachable ({exc}); skipping this job")
        return []
    return build_chunks(papers)


def ingest(*, query: str = "cat:q-fin.*", limit: int = 50, upsert: bool = True) -> int:
    from .common import upsert_chunks

    chunks = collect_chunks(query=query, limit=limit)
    return upsert_chunks(chunks) if upsert else len(chunks)


def _result_to_dict(result: arxiv_api.Result) -> dict[str, object]:
    arxiv_id = result.get_short_id()
    pdf_url = result.pdf_url or (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "")
    return {
        "title": " ".join((result.title or "").split()),
        "abstract": " ".join((result.summary or "").split()),
        "authors": [author.name for author in result.authors],
        "published": result.published.isoformat() if result.published else "",
        "updated": result.updated.isoformat() if result.updated else "",
        "arxiv_id": arxiv_id,
        "categories": list(result.categories or []),
        "source_url": result.entry_id or "",
        "pdf_url": pdf_url,
    }


def _chunks_for_paper(paper: dict[str, object]) -> list[KnowledgeChunk]:
    title = str(paper["title"])
    abstract = str(paper.get("abstract") or "")
    authors = list(paper.get("authors") or [])
    arxiv_id = str(paper.get("arxiv_id") or "")
    year = str(paper.get("published") or "")[:4]
    tags = ["arxiv", "q-fin", *infer_tags(f"{title}\n{abstract}", TOPIC_VOCAB)]

    metadata = {
        "provider": "arxiv",
        "title": title,
        "authors": authors,
        "published": paper.get("published"),
        "updated": paper.get("updated"),
        "arxiv_id": arxiv_id,
        "categories": paper.get("categories"),
        "source_url": paper.get("source_url"),
        "pdf_url": paper.get("pdf_url"),
        "source_type": "paper",
        "citation": _citation(authors, year, title, arxiv_id),
    }
    return chunk_text(
        f"# {title}\n\n{abstract}",
        corpus="papers",
        source=str(paper.get("source_url") or arxiv_id or "arxiv"),
        citation=str(metadata["citation"]),
        tags=tags,
        metadata={k: v for k, v in metadata.items() if v not in (None, "", [])},
    )


def _citation(authors: list[str], year: str, title: str, arxiv_id: str) -> str:
    if authors:
        who = authors[0] if len(authors) == 1 else f"{authors[0]} et al."
    else:
        who = "Unknown"
    bits = [f"{who} ({year})" if year else who, title.rstrip(".")]
    tail = f"arXiv:{arxiv_id}" if arxiv_id else "arXiv"
    return ". ".join([*bits, tail])


def _warn(message: str) -> None:
    print(f"[arxiv] WARNING: {message}", file=sys.stderr)
