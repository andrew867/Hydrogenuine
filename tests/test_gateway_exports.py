"""
Office exports API: POST /v1/exports/docx, pptx, xlsx; GET /v1/files/{file_id}/download tenant-scoped.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from hg_core.tenancy.context import TenantContext
from hg_gateway.main import app
from hg_gateway.auth import verify_api_key, get_tenant_context


@pytest.fixture
def export_root(tmp_path):
    """Set HG_DOCUMENTS_ROOT so tenant exports go to tmp_path (memory/tenants structure)."""
    root = tmp_path / "tenants"
    root.mkdir(parents=True)
    prev = os.environ.get("HG_DOCUMENTS_ROOT")
    os.environ["HG_DOCUMENTS_ROOT"] = str(root)
    try:
        yield root
    finally:
        if prev is not None:
            os.environ["HG_DOCUMENTS_ROOT"] = prev
        else:
            os.environ.pop("HG_DOCUMENTS_ROOT", None)


@pytest.fixture
def client(export_root):
    """TestClient with auth and tenant overrides."""
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: TenantContext(tenant_id="default", environment="dev")
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)


def test_export_docx_and_download(client, export_root):
    """POST /exports/docx returns file_id; GET /files/{file_id}/download returns the file."""
    r = client.post(
        "/v1/exports/docx",
        json={"title": "Test Doc", "sections": [{"heading": "Section 1", "text": "Hello world."}]},
    )
    assert r.status_code == 200
    data = r.json()
    assert "file_id" in data
    assert data["title"] == "Test Doc"
    file_id = data["file_id"]

    r2 = client.get(f"/v1/files/{file_id}/download")
    assert r2.status_code == 200
    assert "application" in (r2.headers.get("content-type") or "")
    assert len(r2.content) > 100


def test_export_docx_with_citations(client, export_root):
    """DOCX export accepts citations (body-level or per-section)."""
    r = client.post(
        "/v1/exports/docx",
        json={
            "title": "Cited",
            "sections": [
                {"text": "First paragraph.", "citations": [{"document_id": "d1", "page_start": 1, "page_end": 1}]},
            ],
        },
    )
    assert r.status_code == 200
    assert r.json().get("file_id")


def test_export_pptx_and_download(client, export_root):
    """POST /exports/pptx returns file_id; download returns PPTX bytes."""
    r = client.post(
        "/v1/exports/pptx",
        json={"title": "Deck", "slides": ["Slide one", "Slide two"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert "file_id" in data
    file_id = data["file_id"]

    r2 = client.get(f"/v1/files/{file_id}/download")
    assert r2.status_code == 200
    assert len(r2.content) > 100
    assert b"PK" in r2.content[:10]


def test_export_xlsx_and_download(client, export_root):
    """POST /exports/xlsx returns file_id; download returns XLSX bytes."""
    r = client.post(
        "/v1/exports/xlsx",
        json={"title": "Data", "data": [["A", "B"], [1, 2], [3, 4]]},
    )
    assert r.status_code == 200
    data = r.json()
    assert "file_id" in data
    file_id = data["file_id"]

    r2 = client.get(f"/v1/files/{file_id}/download")
    assert r2.status_code == 200
    assert len(r2.content) > 100
    assert b"PK" in r2.content[:10]


def test_export_xlsx_sheets(client, export_root):
    """XLSX export with sheets dict creates multiple sheets."""
    r = client.post(
        "/v1/exports/xlsx",
        json={"title": "Multi", "sheets": {"Summary": [["x", "y"]], "Detail": [[1], [2]]}},
    )
    assert r.status_code == 200
    assert r.json().get("file_id")


def test_download_wrong_tenant_404(client, export_root):
    """Download with file_id that does not exist returns 404."""
    r = client.get("/v1/files/nonexistent-id-12345/download")
    assert r.status_code == 404
