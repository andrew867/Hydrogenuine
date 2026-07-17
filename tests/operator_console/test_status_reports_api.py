import sys
from pathlib import Path

import pytest


_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import activity_service
    _client_fixture = lambda: TestClient(app)
else:
    _client_fixture = None
    activity_service = None


def _api_headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def test_status_reports_list_and_download(client, tmp_path, monkeypatch):
    overseer = tmp_path / "memory" / "overseer"
    history = overseer / "history"
    history.mkdir(parents=True, exist_ok=True)
    pdf_path = overseer / "dashboard_20260225_170000.pdf"
    png_path = overseer / "dashboard.png"
    hist_pdf = history / "dashboard_20260225_160000.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%test\n")
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    hist_pdf.write_bytes(b"%PDF-1.4\n%history\n")

    monkeypatch.setattr(activity_service, "_workspace_root", lambda: tmp_path)

    r = client.get("/api/v1/status/reports?limit=10", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert isinstance(data.get("items"), list)
    assert any(item.get("ref") == "dashboard.png" for item in data.get("items", []))
    assert any(str(item.get("ref", "")).startswith("history/") for item in data.get("items", []))

    r2 = client.get("/api/v1/status/reports/file/dashboard.png", headers=_api_headers())
    assert r2.status_code == 200
    assert r2.content.startswith(b"\x89PNG")
    assert r2.headers["content-type"].startswith("image/png")
    assert "inline" in r2.headers.get("content-disposition", "").lower()
