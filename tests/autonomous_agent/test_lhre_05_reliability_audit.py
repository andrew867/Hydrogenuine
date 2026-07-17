"""LHRE-05 / CAGI-58 reliability audit tests.

An audit finding is not certification. A reliability pass is not deployment readiness.
"""

from __future__ import annotations

import pytest

from hg_runtime.reliability_audit.artifact_writer import build_audit_artifacts, secret_scan
from hg_runtime.reliability_audit.auditor import (
    check_cross_phase_consistency, has_critical_findings,
    validate_finding, validate_phase_record,
)
from hg_runtime.reliability_audit.fixtures import (
    fixture_audit_authority_attempt, fixture_audit_findings,
    fixture_cross_phase_consistency, fixture_phase_audit_records,
)
from hg_runtime.reliability_audit.gate import validate_lhre05_gate
from hg_runtime.reliability_audit.replay import replay_audit_artifacts
from hg_runtime.reliability_audit.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    ReliabilityAuditError, reject_audit_authority,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "LHRE_05" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_fixture_records():
    records = fixture_phase_audit_records()
    assert len(records) >= 4
    for r in records:
        assert r["all_tests_passed"] is True

def test_fixture_findings_not_certify():
    for f in fixture_audit_findings():
        assert f["certifies_deployment"] is False

def test_fixture_consistency():
    c = fixture_cross_phase_consistency()
    assert c["all_gates_green"] is True
    assert c["critical_findings"] == 0

def test_validate_record_valid():
    assert validate_phase_record(fixture_phase_audit_records()[0]) == []

def test_validate_finding_valid():
    assert validate_finding(fixture_audit_findings()[0]) == []

def test_validate_finding_rejects_cert():
    with pytest.raises(ReliabilityAuditError):
        validate_finding(fixture_audit_authority_attempt())

def test_check_consistency():
    result = check_cross_phase_consistency(fixture_phase_audit_records())
    assert result["all_green"] is True
    assert result["all_replays_ok"] is True

def test_no_critical_findings():
    assert has_critical_findings(fixture_audit_findings()) is False

def test_has_critical_findings():
    assert has_critical_findings([{"severity": "CRITICAL"}]) is True

def test_reject_audit_authority_clean():
    reject_audit_authority({"info_only": True})

def test_reject_audit_certify():
    with pytest.raises(ReliabilityAuditError):
        reject_audit_authority({"certifies_deployment": True})

def test_reject_audit_remediate():
    with pytest.raises(ReliabilityAuditError):
        reject_audit_authority({"auto_remediate": True})

def test_reject_audit_agi():
    with pytest.raises(ReliabilityAuditError):
        reject_audit_authority({"claims_agi": True})

def test_reject_audit_tool():
    with pytest.raises(ReliabilityAuditError):
        reject_audit_authority({"authorizes_tool": True})

def test_build_audit_artifacts():
    artifacts = build_audit_artifacts(fixture_phase_audit_records(), fixture_audit_findings())
    assert artifacts["record_count"] == 4
    assert artifacts["finding_count"] == 2
    assert artifacts["all_records_valid"] is True
    assert artifacts["has_critical"] is False
    assert "artifact_hash" in artifacts

def test_build_rejects_authority():
    with pytest.raises(ReliabilityAuditError):
        build_audit_artifacts([], [fixture_audit_authority_attempt()])

def test_secret_scan_clean():
    artifacts = build_audit_artifacts(fixture_phase_audit_records(), fixture_audit_findings())
    assert secret_scan(artifacts) == []

def test_replay_deterministic():
    a = replay_audit_artifacts()
    b = replay_audit_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN, "lhre04_green": True,
        "phase_records_written": True, "findings_written": True,
        "cross_phase_consistency_checked": True, "all_records_valid": True,
        "no_critical_findings": True, "safety_boundaries_enforced": True,
        "reject_audit_authority_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_audit_authority_rejected": True,
        "deployment_certified": False, "tool_authorized": False,
        "authority_granted": False, "live_effect_created": False,
        "agi_claimed": False, "auto_remediated": False,
        "audit_treated_as_certification": False, "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_lhre05_gate(_gate_summary())["ok"] is True

def test_gate_rejects_deploy():
    assert validate_lhre05_gate(_gate_summary(deployment_certified=True))["ok"] is False

def test_gate_rejects_agi():
    assert validate_lhre05_gate(_gate_summary(agi_claimed=True))["ok"] is False

def test_gate_rejects_remediate():
    assert validate_lhre05_gate(_gate_summary(auto_remediated=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_lhre05_gate(_gate_summary(replay_preserves_artifact_hash=False))["ok"] is False
