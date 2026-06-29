"""Tests for the sandboxed local-PDF route (/api/pdfs)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import pdfs


def _app_with_roots(roots: list[Path]) -> TestClient:
    app = FastAPI()

    class _Settings:
        pdf_root_paths = roots

    app.state.settings = _Settings()
    app.include_router(pdfs.router)
    return TestClient(app)


# A 4-byte stub that is enough for FileResponse; we only assert routing/containment here.
_PDF_BYTES = b"%PDF-1.4 test body\n%%EOF"


def test_serves_pdf_inside_approved_root(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(_PDF_BYTES)
    client = _app_with_roots([tmp_path.resolve()])

    resp = client.get("/api/pdfs", params={"path": str(pdf)})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == _PDF_BYTES


def test_rejects_non_pdf(tmp_path):
    other = tmp_path / "notes.txt"
    other.write_text("nope", encoding="utf-8")
    client = _app_with_roots([tmp_path.resolve()])
    resp = client.get("/api/pdfs", params={"path": str(other)})
    assert resp.status_code == 400


def test_rejects_path_outside_approved_root(tmp_path):
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "secret.pdf"
    outside.write_bytes(_PDF_BYTES)
    client = _app_with_roots([approved.resolve()])

    resp = client.get("/api/pdfs", params={"path": str(outside)})
    assert resp.status_code == 403


def test_rejects_traversal_escape(tmp_path):
    approved = tmp_path / "approved"
    approved.mkdir()
    secret = tmp_path / "secret.pdf"
    secret.write_bytes(_PDF_BYTES)
    client = _app_with_roots([approved.resolve()])

    # ../secret.pdf resolves outside the approved root
    resp = client.get("/api/pdfs", params={"path": str(approved / ".." / "secret.pdf")})
    assert resp.status_code == 403


def test_missing_pdf_inside_root_is_404(tmp_path):
    client = _app_with_roots([tmp_path.resolve()])
    resp = client.get("/api/pdfs", params={"path": str(tmp_path / "absent.pdf")})
    assert resp.status_code == 404


def test_normalizes_arxiv_abs_and_pdf_urls():
    assert (
        pdfs._normalize_arxiv_pdf_url("http://arxiv.org/abs/2401.05678v2")
        == "https://arxiv.org/pdf/2401.05678v2"
    )
    assert (
        pdfs._normalize_arxiv_pdf_url("https://www.arxiv.org/pdf/hep-th/9901001.pdf")
        == "https://arxiv.org/pdf/hep-th/9901001"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/pdf/2401.05678",
        "file:///tmp/paper.pdf",
        "https://arxiv.org/e-print/2401.05678",
        "https://arxiv.org/pdf/../../secret",
    ],
)
def test_rejects_non_arxiv_proxy_inputs(url):
    with pytest.raises(ValueError):
        pdfs._normalize_arxiv_pdf_url(url)


def test_serves_arxiv_pdf_through_same_origin_proxy(monkeypatch, tmp_path):
    client = _app_with_roots([tmp_path.resolve()])
    seen: list[str] = []

    async def fake_fetch(url: str) -> bytes:
        seen.append(url)
        return _PDF_BYTES

    monkeypatch.setattr(pdfs, "_fetch_arxiv_pdf", fake_fetch)

    resp = client.get("/api/pdfs/arxiv", params={"url": "http://arxiv.org/abs/2401.05678v2"})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["content-disposition"] == 'inline; filename="arxiv-2401.05678v2.pdf"'
    assert resp.content == _PDF_BYTES
    assert seen == ["https://arxiv.org/pdf/2401.05678v2"]
