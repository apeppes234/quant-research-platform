"""Ingest arXiv q-fin preprints -> corpus 'papers' (keyless API). docs/06."""

from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .common import KnowledgeChunk, chunk_text, upsert_chunks

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"


def fetch(query: str = "cat:q-fin.*", *, limit: int = 50) -> list[dict[str, str]]:
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

    papers: list[dict[str, str]] = []
    for entry in root.findall(f"{ATOM}entry"):
        title = _text(entry, "title")
        summary = _text(entry, "summary")
        published = _text(entry, "published")
        paper_id = _text(entry, "id")
        papers.append(
            {
                "title": " ".join(title.split()),
                "summary": " ".join(summary.split()),
                "published": published,
                "url": paper_id,
            }
        )
    return papers


def build_chunks(papers: list[dict[str, str]]) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for paper in papers:
        citation = f"{paper['title']} ({paper.get('published', '')[:10]}), arXiv"
        chunks.extend(
            chunk_text(
                f"# {paper['title']}\n\n{paper['summary']}",
                corpus="papers",
                source=paper["url"],
                citation=citation,
                tags=["arxiv", "q-fin"],
                metadata={"provider": "arxiv", "published": paper.get("published")},
            )
        )
    return chunks


def ingest(*, query: str = "cat:q-fin.*", limit: int = 50, upsert: bool = True) -> int:
    chunks = build_chunks(fetch(query=query, limit=limit))
    return upsert_chunks(chunks) if upsert else len(chunks)


def _text(entry: ET.Element, name: str) -> str:
    child = entry.find(f"{ATOM}{name}")
    return child.text.strip() if child is not None and child.text else ""
