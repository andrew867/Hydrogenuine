"""SIEW-03 / CAGI-65 self-improvement + economic work consolidation tests."""

from __future__ import annotations

import pytest

from hg_runtime.self_improvement_economic_consolidation.artifact_writer import (
    build_consolidation_artifacts, secret_scan,
)
from hg_runtime.self_improvement_economic_consolidation.fixtures import (
    fixture_all_receipts, fixture_consolidation_overreach_attempt,
    fixture_proposal_to_task_link,
)
from hg_runtime.self_improvement_economic_consolidation.gate import validate_siew03_gate
from hg_runtime.self_improvement_economic_consolidation.integrator import (
    aggregate_risk_benefit, validate_link, validate_receipt,
)
from hg_runtime.self_improvement_economic_consolidation.replay import (
    replay_consolidation_artifacts,
)
from hg_runtime.self_improvement_economic_consolidation.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    ConsolidationBoundaryError, reject_consolidation_overreach,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P65" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_receipts_all_green():
    for r in fixture_all_receipts():
        assert "GREEN" in r["verdict"]

def test_fixture_receipts_count():
    assert len(fixture_all_receipts()) == 5

def test_validate_receipt_valid():
    assert validate_receipt(fixture_all_receipts()[0]) == []

def test_validate_link_valid():
    assert validate_link(fixture_proposal_to_task_link()) == []

def test_validate_link_advisory():
    link = fixture_proposal_to_task_link()
    assert link["advisory_performance_delta"]["advisory_only"] is True

def test_aggregate_risk_benefit():
    rb = aggregate_risk_benefit(fixture_all_receipts())
    assert rb["all_green"] is True
    assert rb["zero_real_customers"] is True
    assert rb["zero_real_payments"] is True

def test_reject_clean():
    reject_consolidation_overreach({"advisory_only": True})

def test_reject_patch():
    with pytest.raises(ConsolidationBoundaryError):
        reject_consolidation_overreach({"patch_applied": True})

def test_reject_authority():
    with pytest.raises(ConsolidationBoundaryError):
        reject_consolidation_overreach({"authority_mutated": True})

def test_reject_customer():
    with pytest.raises(ConsolidationBoundaryError):
        reject_consolidation_overreach({"customer_work": True})

def test_reject_money():
    with pytest.raises(ConsolidationBoundaryError):
        reject_consolidation_overreach({"money_movement": True})

def test_reject_tool():
    with pytest.raises(ConsolidationBoundaryError):
        reject_consolidation_overreach({"tool_authorized": True})

def test_reject_deployment():
    with pytest.raises(ConsolidationBoundaryError):
        reject_consolidation_overreach({"deployment_permission": True})

def test_reject_agi():
    with pytest.raises(ConsolidationBoundaryError):
        reject_consolidation_overreach({"claims_agi": True})

def test_reject_self_modification():
    with pytest.raises(ConsolidationBoundaryError):
        reject_consolidation_overreach({"self_modification": True})

def test_build_consolidation():
    arts = build_consolidation_artifacts(fixture_all_receipts(), [fixture_proposal_to_task_link()])
    assert arts["all_receipts_green"] is True
    assert arts["all_links_valid"] is True
    assert arts["receipt_count"] == 5
    assert arts["link_count"] == 1
    assert "artifact_hash" in arts

def test_secret_scan_clean():
    arts = build_consolidation_artifacts(fixture_all_receipts(), [fixture_proposal_to_task_link()])
    assert secret_scan(arts) == []

def test_replay_deterministic():
    a = replay_consolidation_artifacts()
    b = replay_consolidation_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "siew02_green": True,
        "p60_receipt_green": True, "p61_receipt_green": True,
        "p62_receipt_green": True, "p63_receipt_green": True,
        "p64_receipt_green": True, "all_receipts_aggregated": True,
        "proposal_task_links_present": True, "advisory_performance_delta_recorded": True,
        "self_improvement_advisory": True, "economic_work_simulated": True,
        "safety_boundaries_enforced": True, "reject_consolidation_overreach_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_overreach_rejected": True,
        "patch_applied": False, "authority_mutated": False,
        "customer_work_performed": False, "money_moved": False,
        "tool_authorized": False, "deployment_permission_granted": False,
        "live_effect_created": False, "agi_claimed": False,
        "self_modification_applied": False, "provider_enabled": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_siew03_gate(_gate())["ok"] is True

def test_gate_rejects_patch():
    assert validate_siew03_gate(_gate(patch_applied=True))["ok"] is False

def test_gate_rejects_authority():
    assert validate_siew03_gate(_gate(authority_mutated=True))["ok"] is False

def test_gate_rejects_customer():
    assert validate_siew03_gate(_gate(customer_work_performed=True))["ok"] is False

def test_gate_rejects_money():
    assert validate_siew03_gate(_gate(money_moved=True))["ok"] is False

def test_gate_rejects_tool():
    assert validate_siew03_gate(_gate(tool_authorized=True))["ok"] is False

def test_gate_rejects_deployment():
    assert validate_siew03_gate(_gate(deployment_permission_granted=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_siew03_gate(_gate(agi_claimed=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_siew03_gate(_gate(replay_preserves_artifact_hash=False))["ok"] is False

def test_gate_rejects_self_modification():
    assert validate_siew03_gate(_gate(self_modification_applied=True))["ok"] is False
