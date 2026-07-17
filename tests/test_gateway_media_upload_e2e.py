"""
Pack2-09: Moltx media upload 501 contract e2e. Real gateway; endpoint returns 501 with structured error for UI branching.
"""

import os
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key


@pytest.fixture
def client_sqlite(tmp_path):
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    store_module._store = None
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        os.environ.pop("HG_GATEWAY_STORE", None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_media_upload_returns_501_with_structured_error(client_sqlite):
    """POST /v1/media/upload returns 501 and body with error + message so UI can branch."""
    r = client_sqlite.post("/v1/media/upload")
    assert r.status_code == 501
    data = r.json()
    assert data.get("error") == "media_upload_unsupported"
    assert "message" in data
    assert "not supported" in data["message"].lower()
