"""Ingest arXiv q-fin preprints -> corpus 'papers' (keyless API). docs/06.

arXiv is the **automated** academic feed (contrast SSRN, which is curated/manual). It hits arXiv's
public Atom API, so it needs no key. Results are research grounding/citations for the Paper Agent — not
a price/return source; every hypothesis is validated later by a QuantConnect backtest.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .common import KnowledgeChunk, chunk_text, infer_tags

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

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
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": max(1, min(limit, 100)),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    with urllib.request.urlopen(f"{ARXIV_API}?{params}", timeout=45) as response:
        root = ET.fromstring(response.read())

    papers: list[dict[str, object]] = []
    for entry in root.findall(f"{ATOM}entry"):
        try:
            papers.append(_parse_entry(entry))
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
    """Fetch + chunk, degrading to an empty list (with a warning) on network failure."""

    try:
        papers = fetch(query=query, limit=limit or 50)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        _warn(f"arXiv API unreachable ({exc}); skipping this job")
        return []
    return build_chunks(papers)


def ingest(*, query: str = "cat:q-fin.*", limit: int = 50, upsert: bool = True) -> int:
    from .common import upsert_chunks

    chunks = collect_chunks(query=query, limit=limit)
    return upsert_chunks(chunks) if upsert else len(chunks)


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


def _parse_entry(entry: ET.Element) -> dict[str, object]:
    title = " ".join(_text(entry, "title").split())
    abstract = " ".join(_text(entry, "summary").split())
    abs_url = _text(entry, "id")
    arxiv_id = abs_url.rsplit("/abs/", 1)[-1] if "/abs/" in abs_url else abs_url

    authors = [
        name.text.strip()
        for author in entry.findall(f"{ATOM}author")
        if (name := author.find(f"{ATOM}name")) is not None and name.text
    ]
    categories = [
        cat.attrib["term"] for cat in entry.findall(f"{ATOM}category") if cat.attrib.get("term")
    ]

    pdf_url = ""
    for link in entry.findall(f"{ATOM}link"):
        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
            pdf_url = link.attrib.get("href", "")
    if not pdf_url and arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "published": _text(entry, "published"),
        "updated": _text(entry, "updated"),
        "arxiv_id": arxiv_id,
        "categories": categories,
        "source_url": abs_url,
        "pdf_url": pdf_url,
    }


def _citation(authors: list[str], year: str, title: str, arxiv_id: str) -> str:
    if authors:
        who = authors[0] if len(authors) == 1 else f"{authors[0]} et al."
    else:
        who = "Unknown"
    bits = [f"{who} ({year})" if year else who, title.rstrip(".")]
    tail = f"arXiv:{arxiv_id}" if arxiv_id else "arXiv"
    return ". ".join([*bits, tail])


def _text(entry: ET.Element, name: str) -> str:
    child = entry.find(f"{ATOM}{name}")
    return child.text.strip() if child is not None and child.text else ""


def _warn(message: str) -> None:
    print(f"[arxiv] WARNING: {message}", file=sys.stderr)
