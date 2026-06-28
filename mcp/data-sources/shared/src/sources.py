"""HTTP-backed PIT data source helpers."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


async def fred_observations(
    *,
    series_id: str,
    observation_start: str | None = None,
    observation_end: str | None = None,
    as_of: str | None = None,
    limit: int = 5000,
) -> dict[str, Any]:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is required for FRED/ALFRED pulls")
    vintage = as_of or now_iso()[:10]
    params: dict[str, Any] = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "realtime_start": vintage,
        "realtime_end": vintage,
        "limit": max(1, min(limit, 100000)),
    }
    if observation_start:
        params["observation_start"] = observation_start
    if observation_end:
        params["observation_end"] = observation_end

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.get("https://api.stlouisfed.org/fred/series/observations", params=params)
        response.raise_for_status()
        payload = response.json()

    return {
        "source": "FRED/ALFRED",
        "series_id": series_id,
        "as_of": vintage,
        "citation": f"ALFRED vintage {vintage} for {series_id}",
        "observations": payload.get("observations", []),
        "metadata": {"realtime_start": vintage, "realtime_end": vintage},
    }


async def edgar_company_filings(
    *,
    cik: str,
    form_type: str | None = None,
    filed_after: str | None = None,
    filed_before: str | None = None,
    as_of: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    user_agent = os.getenv("SEC_EDGAR_USER_AGENT")
    if not user_agent:
        raise RuntimeError("SEC_EDGAR_USER_AGENT is required by SEC EDGAR")
    normalized_cik = str(cik).strip().lstrip("0").zfill(10)
    as_of_date = (as_of or now_iso())[:10]
    url = f"https://data.sec.gov/submissions/CIK{normalized_cik}.json"
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}

    async with httpx.AsyncClient(timeout=45, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()

    recent = payload.get("filings", {}).get("recent", {})
    rows = []
    for idx, accession in enumerate(recent.get("accessionNumber", [])):
        filing_date = _item(recent, "filingDate", idx)
        form = _item(recent, "form", idx)
        if filing_date > as_of_date:
            continue
        if form_type and form != form_type:
            continue
        if filed_after and filing_date < filed_after:
            continue
        if filed_before and filing_date > filed_before:
            continue
        rows.append(
            {
                "accession_number": accession,
                "filing_date": filing_date,
                "report_date": _item(recent, "reportDate", idx),
                "form": form,
                "primary_document": _item(recent, "primaryDocument", idx),
            }
        )
        if len(rows) >= limit:
            break

    return {
        "source": "SEC EDGAR submissions",
        "cik": normalized_cik,
        "as_of": as_of_date,
        "citation": f"SEC EDGAR CIK{normalized_cik} filings as filed by {as_of_date}",
        "filings": rows,
    }


async def gdelt_doc_search(
    *,
    query: str,
    start_datetime: str,
    end_datetime: str,
    as_of: str | None = None,
    max_records: int = 75,
) -> dict[str, Any]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "startdatetime": start_datetime,
        "enddatetime": end_datetime,
        "maxrecords": max(1, min(max_records, 250)),
    }
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params)
        response.raise_for_status()
        payload = response.json()
    as_of_value = as_of or end_datetime
    return {
        "source": "GDELT DOC 2.0",
        "as_of": as_of_value,
        "citation": f"GDELT documents for {query!r}, {start_datetime} to {end_datetime}",
        "articles": payload.get("articles", []),
    }


async def arxiv_qfin_search(*, query: str, max_results: int = 20, as_of: str | None = None) -> dict[str, Any]:
    import urllib.parse
    import xml.etree.ElementTree as ET

    params = urllib.parse.urlencode(
        {
            "search_query": f"cat:q-fin.* AND all:{query}",
            "start": 0,
            "max_results": max(1, min(max_results, 100)),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.get(f"https://export.arxiv.org/api/query?{params}")
        response.raise_for_status()

    atom = "{http://www.w3.org/2005/Atom}"
    root = ET.fromstring(response.text)
    papers = []
    as_of_value = as_of or now_iso()
    for entry in root.findall(f"{atom}entry"):
        published = _xml_text(entry, "published", atom)
        if published and published[:10] > as_of_value[:10]:
            continue
        papers.append(
            {
                "title": " ".join(_xml_text(entry, "title", atom).split()),
                "summary": " ".join(_xml_text(entry, "summary", atom).split()),
                "published": published,
                "url": _xml_text(entry, "id", atom),
            }
        )
    return {
        "source": "arXiv q-fin",
        "as_of": as_of_value,
        "citation": f"arXiv q-fin search {query!r} as of {as_of_value[:10]}",
        "papers": papers,
    }


def _item(payload: dict[str, list[Any]], key: str, index: int) -> str:
    values = payload.get(key, [])
    if index >= len(values):
        return ""
    return str(values[index] or "")


def _xml_text(entry: Any, name: str, atom: str) -> str:
    child = entry.find(f"{atom}{name}")
    return child.text.strip() if child is not None and child.text else ""
