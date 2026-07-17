from __future__ import annotations

from pathlib import Path

import pytest

from hg_learning.feedback.incidents import LearningIncidentStore
from hg_learning.feedback.shadow_ledger import ShadowLedger
from hg_learning.guardrails.reward_integrity import RewardIntegrityMonitor


@pytest.fixture
def learning_db(tmp_path: Path, monkeypatch) -> Path:
    db = tmp_path / "learning.sqlite3"
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(db))
    return db


def test_goodhart_freeze_and_unfreeze_path(learning_db: Path):
    ledger = ShadowLedger(learning_db)
    monitor = RewardIntegrityMonitor(ledger, freeze_enabled=True, min_samples=5)
    path = "symmetry_feedback"
    for i in range(6):
        proxy = 0.9 - i * 0.05
        truth = 0.2 + i * 0.08
        alert = monitor.record(path, proxy_rate=proxy, ground_truth_rate=truth)
    assert ledger.is_path_frozen(path)
    assert alert is not None
    assert alert.get("frozen") is True

    assert ledger.unfreeze_path(path) is True
    assert not ledger.is_path_frozen(path)


def test_incident_file_and_resolve(learning_db: Path):
    incidents = LearningIncidentStore(learning_db)
    incident_id = incidents.file_incident(
        "goodhart_divergence",
        path_name="symmetry_feedback",
        evidence={"correlation": -0.5},
    )
    open_list = incidents.list_open()
    assert len(open_list) == 1
    assert open_list[0]["incident_id"] == incident_id
    assert incidents.resolve(incident_id) is True
    assert incidents.list_open() == []


def test_parameter_freeze_unfreeze(learning_db: Path):
    ledger = ShadowLedger(learning_db)
    ledger.freeze_parameter(
        "symmetry_breaker.default_delta",
        "symmetry_feedback",
        "oscillation",
        [{"proposed_value": 0.1}, {"proposed_value": 0.2}],
    )
    assert ledger.is_parameter_frozen("symmetry_breaker.default_delta")
    assert ledger.unfreeze_parameter("symmetry_breaker.default_delta") is True
    assert not ledger.is_parameter_frozen("symmetry_breaker.default_delta")
