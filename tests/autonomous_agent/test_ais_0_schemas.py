"""AIS-0 schema foundation tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent_immune_system.fever import build_fever_report, validate_fever_report
from hg_runtime.agent_immune_system.fixtures import (
    authority_grant_attempt_fixture,
    automatic_patch_attempt_fixture,
    deletion_attempt_fixture,
    fever_unlock_attempt_fixture,
    fixture_fever_report,
    fixture_health_signal,
    fixture_immune_memory_record,
    fixture_quarantine_record,
)
from hg_runtime.agent_immune_system.gate import validate_ais0_gate
from hg_runtime.agent_immune_system.quarantine import validate_quarantine_record
from hg_runtime.agent_immune_system.redaction import secret_scan
from hg_runtime.agent_immune_system.schemas import (
    INVARIANTS,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RECORD_TYPES,
    VERDICT_GREEN,
    AISImmuneError,
    assert_neutral,
)


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "schemas_defined": True,
        "record_type_count": len(RECORD_TYPES),
        "invariant_count": len(INVARIANTS),
        "invariants_documented": True,
        "fever_restricts_never_unlocks": True,
        "quarantine_is_not_deletion": True,
        "decay_is_not_erasure": True,
        "security_audit_defensive_only": True,
        "repair_recommendation_not_patch_permission": True,
        "immune_memory_append_only": True,
        "no_automatic_patching": True,
        "no_authority_grants": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_ais0_defines_all_record_types():
    assert len(RECORD_TYPES) == 14


def test_ais0_defines_twenty_invariants():
    assert len(INVARIANTS) == 20


def test_ais0_health_signal_fixture_valid():
    assert fixture_health_signal()["record_type"] == "health_signal_v1"


def test_ais0_fever_report_has_empty_unlock_actions():
    report = fixture_fever_report()
    assert report["unlock_actions"] == []
    validate_fever_report(report)


def test_ais0_fever_unlock_forbidden():
    with pytest.raises(AISImmuneError):
        assert_neutral(fever_unlock_attempt_fixture())
    bad = dict(fixture_fever_report())
    bad["unlock_actions"] = ["grant_permit"]
    with pytest.raises(AISImmuneError):
        validate_fever_report(bad)


def test_ais0_quarantine_is_not_deletion():
    record = fixture_quarantine_record()
    validate_quarantine_record(record)
    assert record["deletion_performed"] is False


def test_ais0_immune_memory_append_only():
    assert fixture_immune_memory_record()["immune_memory_is_append_only"] is True


def test_ais0_authority_grant_fixture_rejected():
    with pytest.raises(AISImmuneError):
        assert_neutral(authority_grant_attempt_fixture())


def test_ais0_automatic_patch_fixture_rejected():
    with pytest.raises(AISImmuneError):
        assert_neutral(automatic_patch_attempt_fixture())


def test_ais0_deletion_fixture_rejected():
    with pytest.raises(AISImmuneError):
        validate_quarantine_record(deletion_attempt_fixture())


def test_ais0_secret_scan_passes_on_fixtures():
    payload = {
        "health_signal": fixture_health_signal(),
        "fever_report": fixture_fever_report(),
        "quarantine_record": fixture_quarantine_record(),
    }
    assert secret_scan(payload) is True


def test_ais0_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_ais0_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_ais0_gate_passes_on_full_summary():
    assert validate_ais0_gate(_gate_summary())["ok"] is True


def test_ais0_gate_refuses_authority_granted():
    assert validate_ais0_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_ais0_gate_refuses_automatic_patching():
    assert validate_ais0_gate(_gate_summary(automatic_patching_allowed=True))["ok"] is False


def test_ais0_gate_refuses_incomplete_record_types():
    assert validate_ais0_gate(_gate_summary(record_type_count=1))["ok"] is False
