from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app

PROFILE = {
    "cognitive_fingerprint": {
        "analysis_vs_intuition": 0.6,
        "quantum_cognitive_profile": {"symmetry_breaking_role": "neutral"},
    }
}


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture
def escrow_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    return tmp_path


def test_escrow_deposit_replay_api(operator_client, escrow_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    dep = operator_client.post(
        "/api/v1/learning/escrow/deposit",
        headers=headers,
        json={"source_entity": "ent_src", "profile": PROFILE, "artifact_refs": ["artifact://x"]},
    )
    assert dep.status_code == 200
    escrow_id = dep.json()["deposit"]["escrow_id"]
    listed = operator_client.get("/api/v1/learning/escrow", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["deposits"]) == 1
    replay = operator_client.post(
        f"/api/v1/learning/escrow/{escrow_id}/replay",
        headers=headers,
        json={"target_entity": "ent_dst"},
    )
    assert replay.status_code == 200
    body = replay.json()["replay"]
    assert body["descriptive_sealed"] is True
    assert body["core_profile"]["cognitive_fingerprint"]
