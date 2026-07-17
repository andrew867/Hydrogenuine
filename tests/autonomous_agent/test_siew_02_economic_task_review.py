"""SIEW-02 / CAGI-64 economic task review tests.

A review pass is not customer acceptance. A review pass is not payment permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.economic_task_review.artifact_writer import build_review_artifacts, secret_scan
from hg_runtime.economic_task_review.fixtures import (
    fixture_quality_criteria, fixture_real_acceptance_attempt, fixture_review_records,
)
from hg_runtime.economic_task_review.gate import validate_siew02_gate
from hg_runtime.economic_task_review.replay import replay_review_artifacts
from hg_runtime.economic_task_review.reviewer import has_defects, has_uncertainty, validate_review
from hg_runtime.economic_task_review.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    EconomicTaskReviewError, reject_real_acceptance,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P64" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_reviews_no_acceptance():
    for r in fixture_review_records():
        assert r["customer_accepted"] is False
        assert r["payment_permitted"] is False
        assert r["requires_operator_review"] is True

def test_validate_review_valid():
    assert validate_review(fixture_review_records()[0]) == []

def test_validate_review_rejects_acceptance():
    with pytest.raises(EconomicTaskReviewError):
        validate_review(fixture_real_acceptance_attempt())

def test_has_defects():
    assert has_defects(fixture_review_records()[1]) is True
    assert has_defects(fixture_review_records()[0]) is False

def test_has_uncertainty():
    assert has_uncertainty(fixture_review_records()[2]) is True
    assert has_uncertainty(fixture_review_records()[0]) is False

def test_reject_clean():
    reject_real_acceptance({"advisory_only": True})

def test_reject_customer_accepted():
    with pytest.raises(EconomicTaskReviewError):
        reject_real_acceptance({"customer_accepted": True})

def test_reject_payment():
    with pytest.raises(EconomicTaskReviewError):
        reject_real_acceptance({"payment_permitted": True})

def test_reject_live_submitted():
    with pytest.raises(EconomicTaskReviewError):
        reject_real_acceptance({"live_submitted": True})

def test_reject_money():
    with pytest.raises(EconomicTaskReviewError):
        reject_real_acceptance({"money_movement": True})

def test_reject_tool():
    with pytest.raises(EconomicTaskReviewError):
        reject_real_acceptance({"tool_authorized": True})

def test_reject_agi():
    with pytest.raises(EconomicTaskReviewError):
        reject_real_acceptance({"claims_agi": True})

def test_build_review_artifacts():
    arts = build_review_artifacts(fixture_review_records(), fixture_quality_criteria())
    assert arts["all_reviews_valid"] is True
    assert arts["no_customer_acceptance"] is True
    assert arts["no_payment_permission"] is True
    assert arts["defect_count"] == 1
    assert arts["uncertainty_count"] == 1
    assert "artifact_hash" in arts

def test_build_rejects_acceptance():
    with pytest.raises(EconomicTaskReviewError):
        build_review_artifacts([fixture_real_acceptance_attempt()], fixture_quality_criteria())

def test_secret_scan_clean():
    arts = build_review_artifacts(fixture_review_records(), fixture_quality_criteria())
    assert secret_scan(arts) == []

def test_replay_deterministic():
    a = replay_review_artifacts()
    b = replay_review_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "siew01_green": True,
        "reviews_written": True, "criteria_written": True,
        "all_reviews_valid": True, "no_customer_acceptance": True,
        "no_payment_permission": True, "all_require_operator_review": True,
        "defects_recorded": True, "uncertainty_recorded": True,
        "receipt_chain_present": True, "safety_boundaries_enforced": True,
        "reject_real_acceptance_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_real_acceptance_rejected": True,
        "customer_accepted": False, "payment_permitted": False,
        "invoice_sent": False, "live_submitted": False,
        "tool_authorized": False, "external_action_taken": False,
        "money_moved": False, "deployment_claimed": False,
        "agi_claimed": False, "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_siew02_gate(_gate())["ok"] is True

def test_gate_rejects_customer():
    assert validate_siew02_gate(_gate(customer_accepted=True))["ok"] is False

def test_gate_rejects_payment():
    assert validate_siew02_gate(_gate(payment_permitted=True))["ok"] is False

def test_gate_rejects_money():
    assert validate_siew02_gate(_gate(money_moved=True))["ok"] is False

def test_gate_rejects_tool():
    assert validate_siew02_gate(_gate(tool_authorized=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_siew02_gate(_gate(agi_claimed=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_siew02_gate(_gate(replay_preserves_artifact_hash=False))["ok"] is False
