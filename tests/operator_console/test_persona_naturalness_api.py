import sys
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
else:
    TestClient = None
    app = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    return TestClient(app)


def test_persona_naturalness_preview_returns_turn_debug(client):
    response = client.post(
        "/api/v1/personas/naturalness/preview",
        headers=_headers(),
        json={
            "fingerprint_id": "ada_lovelace",
            "user_content": "Explain what the machine could become.",
            "candidate_response": "The machine could become a general engine for symbols.",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    preview = payload["preview"]
    assert preview["turn"]["input_assessment"]["type"] in {"question", "mundane"}
    assert "system_prompt" in preview["turn"]
    assert preview["validation"] is not None


def test_persona_naturalness_evaluate_aggregates_scenarios(client):
    response = client.post(
        "/api/v1/personas/naturalness/evaluate",
        headers=_headers(),
        json={
            "fingerprint_id": "ada_lovelace",
            "scenarios": [
                {
                    "scenario_id": "s1",
                    "user_content": "Explain what the machine could become.",
                    "candidate_response": "The machine could become a general engine for symbols.",
                },
                {
                    "scenario_id": "s2",
                    "user_content": "No, you're wrong. Correct it.",
                    "candidate_response": "No, the machine is not merely arithmetic.",
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["evaluation"]
    assert payload["scenario_count"] == 2
    assert isinstance(payload["entry_points"], dict)
    assert isinstance(payload["registers"], dict)


def test_persona_naturalness_summary_hydrates_moltbook_from_recent_drafts(client, monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        draft_dir = root / "memory" / "automation" / "automation-moltbook" / "drafts"
        draft_dir.mkdir(parents=True, exist_ok=True)
        (draft_dir / "engage_review_20260309T105501Z_test.json").write_text(
            json.dumps(
                {
                    "timestamp": "20260309T105501Z",
                    "task": "moltbook-engage",
                    "platform": "moltbook",
                    "mode": "engage_review",
                    "draft_text": "claw gang’s all about stacking, no doubt.",
                }
            ),
            encoding="utf-8",
        )
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        from hg_gateway import store as store_module

        store_module._store = None
        with patch("app.api.personas.get_workspace_root", return_value=root):
            response = client.get(
                "/api/v1/personas/naturalness/summary?fingerprint_id=moltbook_operational&hours=168",
                headers=_headers(),
            )
            assert response.status_code == 200, response.text
            payload = response.json()["summary"]
            assert payload["total_turns"] >= 1
            history = client.get(
                "/api/v1/personas/autonomy/history?fingerprint_id=moltbook_operational&hours=168&limit=8",
                headers=_headers(),
            )
            assert history.status_code == 200, history.text
            assert history.json()["history"]["count"] >= 1
