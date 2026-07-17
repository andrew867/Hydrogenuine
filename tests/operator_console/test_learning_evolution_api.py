from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hg_learning.contracts import CorpusOrigin, LearningSignal, LearningSignalType, OutcomeVerdict
from hg_learning.flywheel.corpus_store import CorpusStore
from hg_learning.flywheel.label_store import LabelStore
from hg_learning.flywheel.outcome_labeler import OutcomeLabeler
from operator_console.server.app.main import app as operator_app


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


@pytest.fixture
def evolution_workspace(tmp_path, monkeypatch):
    db = tmp_path / "memory" / "learning" / "corpus.sqlite3"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(db))
    corpus = CorpusStore(db)
    labels = LabelStore(db)
    labeler = OutcomeLabeler(corpus, labels)
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    for i in range(25):
        ts = (base + timedelta(days=i % 10)).isoformat().replace("+00:00", "Z")
        sig = LearningSignal(
            signal_id=f"api_sig_{i}",
            bundle_id=f"b{i}",
            signal_type=LearningSignalType.SWARM_OUTCOME if i % 2 == 0 else LearningSignalType.BEHAVIORAL_TEST,
            payload={"syndrome_count": 3 if i < 15 else 0},
            entity_ids=["api_entity"],
            observed_at=ts,
        )
        corpus.append(sig, origin=CorpusOrigin.MINED, bundle_path="p")
        labeler.label_automated(sig.signal_id, OutcomeVerdict.SUCCESS if i >= 12 else OutcomeVerdict.PARTIAL, confidence=0.9)
    return tmp_path


def test_evolution_propose_approve_lineage_api(operator_client, evolution_workspace):
    headers = {"Authorization": "Bearer test-api-key"}
    profile = {
        "cognitive_fingerprint": {
            "agreement_tendency": 0.5,
            "quantum_cognitive_profile": {"noise_resilience": 0.5, "symmetry_breaking_role": "neutral"},
            "embodiment_profile": {"physical_caution": 0.7},
        },
    }
    proposed = operator_client.post(
        "/api/v1/learning/evolution/propose",
        headers=headers,
        json={"entity_id": "api_entity", "profile": profile},
    )
    assert proposed.status_code == 200, proposed.text
    body = proposed.json()
    assert body["ok"] is True
    if body.get("proposal"):
        pid = body["proposal"]["proposal_id"]
        approved = operator_client.post(
            f"/api/v1/learning/evolution/proposals/{pid}/approve",
            headers=headers,
            json={"operator_id": "operator"},
        )
        assert approved.status_code == 200
        assert approved.json()["ok"] is True
    lineage = operator_client.get("/api/v1/learning/lineage/api_entity", headers=headers)
    assert lineage.status_code == 200
    assert lineage.json()["ok"] is True
