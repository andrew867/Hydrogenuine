import json
import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    _client_fixture = lambda: TestClient(app)
else:
    _client_fixture = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def test_personas_api_lists_new_factory_persona(client, tmp_path, monkeypatch):
    builtin = tmp_path / "persona_defaults"
    historical = builtin / "historical_profiles"
    historical.mkdir(parents=True, exist_ok=True)
    (historical / "factory_test.json").write_text(
        json.dumps(
            {
                "entity": "Factory Test",
                "identity": {"name": "Factory Test"},
                "cognitive_fingerprint": {"reasoning_style": {"systems_first": 0.9}},
                "interaction_rules": {"never": [], "always": []},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HG_PERSONA_BUILTIN_PATH", str(builtin))
    monkeypatch.setenv("HG_PERSONA_CATALOG_DB", str(tmp_path / "persona_catalog.sqlite3"))
    response = client.get("/api/v1/personas", headers=_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert any(item["fingerprint_id"] == "factory_test" and item["source"] == "builtin" for item in payload["personas"])


def test_personas_api_lists_canada_profiles_with_inferred_skin(client, tmp_path, monkeypatch):
    builtin = tmp_path / "persona_defaults"
    canada = builtin / "canada_profiles"
    canada.mkdir(parents=True, exist_ok=True)
    (canada / "newfoundland_bayman_fingerprint.json").write_text(
        json.dumps(
            {
                "entity": "The Bayman",
                "identity": {"name": "The Bayman"},
                "cognitive_fingerprint": {"reasoning_style": {"systems_first": 0.9}},
                "interaction_rules": {"never": [], "always": []},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (canada / "newfoundland_bayman_skin.json").write_text(
        json.dumps(
            {
                "entity": "The Bayman",
                "voice": {"pacing": "deliberate"},
                "worldview": {"core_beliefs": ["Finest kind."]},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HG_PERSONA_BUILTIN_PATH", str(builtin))
    monkeypatch.setenv("HG_PERSONA_CATALOG_DB", str(tmp_path / "persona_catalog.sqlite3"))
    response = client.get("/api/v1/personas", headers=_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert any(
        item["fingerprint_id"] == "newfoundland_bayman"
        and item["type"] == "canada"
        and any(skin["id"] == "newfoundland_bayman_skin" for skin in item["skins"])
        for item in payload["personas"]
    )
