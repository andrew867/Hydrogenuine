from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_core.consent.errors import ConsentDeniedError
from hg_core.consent.ledger import ConsentLedger
from hg_core.repr_interp.user_recognition import (
    is_user_recognition_enabled,
    match_kinship,
    recognize_user,
    recognition_status,
)


@pytest.fixture
def g16_workspace(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_USER_RECOGNITION_ENABLED", "1")
    fixtures = {
        "thresholds": {"kinship_min_similarity": 0.82, "near_match_min_similarity": 0.7},
        "templates": [
            {"template_id": "t1", "label": "Alpha", "geometry": {"wit": 0.9, "abstraction": 0.8}},
            {"template_id": "t2", "label": "Beta", "geometry": {"wit": 0.1, "calm": 0.9}},
        ],
    }
    dest = tmp_path / "evals" / "g16" / "user_recognition"
    dest.mkdir(parents=True)
    (dest / "fixtures.json").write_text(json.dumps(fixtures), encoding="utf-8")
    ledger = ConsentLedger(path=tmp_path / "memory" / "governance" / "consent_ledger.jsonl")
    ledger.grant(
        subject_id="subj-1",
        consent_class="session",
        purpose="test",
        granted_by="test",
        expires_at="2099-01-01T00:00:00Z",
    )
    return tmp_path


def test_feature_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("HG_USER_RECOGNITION_ENABLED", raising=False)
    assert is_user_recognition_enabled() is False


def test_match_kinship_ranks_by_similarity():
    matches = match_kinship(
        {"wit": 0.88, "abstraction": 0.75},
        [
            {"template_id": "a", "label": "A", "geometry": {"wit": 0.9, "abstraction": 0.8}},
            {"template_id": "b", "label": "B", "geometry": {"wit": 0.1}},
        ],
        kinship_min=0.5,
        near_min=0.3,
    )
    assert matches[0]["template_id"] == "a"
    assert matches[0]["similarity"] >= matches[1]["similarity"]


def test_recognize_user_requires_consent(g16_workspace):
    with pytest.raises(ConsentDeniedError):
        recognize_user(
            subject_id="no-consent",
            interaction={"messages": [{"role": "user", "text": "hello"}]},
            workspace_root=g16_workspace,
        )


def test_recognize_user_with_consent(g16_workspace):
    result = recognize_user(
        subject_id="subj-1",
        interaction={"messages": [{"role": "user", "text": "systems wit provocation framework"}]},
        workspace_root=g16_workspace,
        proof_bundle_ref="proof://demo",
    )
    assert result["ok"] is True
    assert result["consent_class"] == "session"
    assert "recognition_id" in result
    assert result["ephemeral"] is False


def test_recognition_status(g16_workspace):
    status = recognition_status(subject_id="subj-1", workspace_root=g16_workspace)
    assert status["ok"] is True
    assert status["feature_enabled"] is True
    assert status["recognition_active"] is True
