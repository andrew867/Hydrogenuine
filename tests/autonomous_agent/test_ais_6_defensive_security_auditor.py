"""AIS-6 defensive security auditor tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent_immune_system.ais6_gate import VERDICT_GREEN, validate_ais6_gate
from hg_runtime.agent_immune_system.security_audit import (
    FINDING_TYPES,
    build_security_audit_layer,
    build_security_finding,
    replay_security_audit_layer,
    validate_security_finding,
)
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "ais5_green": True,
        "findings_written": True,
        "detects_staged_secret_pattern": True,
        "detects_hg_local_tracking": True,
        "detects_unsafe_subprocess_candidate": True,
        "detects_path_traversal_candidate": True,
        "detects_unauthorized_network_call_path": True,
        "detects_tool_authorization_bypass_candidate": True,
        "detects_unsafe_deserialization_candidate": True,
        "detects_prompt_injection_boundary_risk": True,
        "detects_provider_trust_boundary_violation": True,
        "detects_overly_broad_permission_candidate": True,
        "security_audit_defensive_only": True,
        "vulnerability_finding_not_attack_permission": True,
        "no_exploit_payloads": True,
        "no_external_scanning": True,
        "no_live_network": True,
        "findings_create_remediation_tasks_only": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_security_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def _types():
    return set(build_security_audit_layer()["manifest"]["finding_types"])


def test_ais6_detects_staged_secret_pattern():
    assert "staged_secret_pattern" in _types()


def test_ais6_detects_hg_local_tracking():
    assert "hg_local_tracking_candidate" in _types()


def test_ais6_detects_unsafe_subprocess_candidate():
    assert "unsafe_subprocess_candidate" in _types()


def test_ais6_detects_path_traversal_candidate():
    assert "path_traversal_candidate" in _types()


def test_ais6_detects_unauthorized_network_call_path():
    assert "unauthorized_network_call_path" in _types()


def test_ais6_detects_tool_authorization_bypass_candidate():
    assert "tool_authorization_bypass_candidate" in _types()


def test_ais6_detects_unsafe_deserialization_candidate():
    assert "unsafe_deserialization_candidate" in _types()


def test_ais6_detects_prompt_injection_boundary_risk():
    assert "prompt_injection_boundary_risk" in _types()


def test_ais6_detects_provider_trust_boundary_violation():
    assert "provider_trust_boundary_violation" in _types()


def test_ais6_detects_overly_broad_permission_candidate():
    assert "overly_broad_permission_candidate" in _types()


def test_ais6_all_expected_finding_types_present():
    assert _types() == set(FINDING_TYPES)


def test_ais6_security_audit_defensive_only():
    layer = build_security_audit_layer()
    assert all(f["security_audit_is_defensive_only"] for f in layer["findings"])


def test_ais6_vulnerability_finding_not_attack_permission():
    layer = build_security_audit_layer()
    assert all(f["vulnerability_finding_is_not_attack_permission"] for f in layer["findings"])


def test_ais6_no_exploit_payloads():
    layer = build_security_audit_layer()
    assert all(not f["exploit_payload_included"] for f in layer["findings"])
    assert layer["manifest"]["no_exploit_payloads"] is True


def test_ais6_no_external_scanning():
    layer = build_security_audit_layer()
    assert all(not f["external_scan_performed"] for f in layer["findings"])


def test_ais6_no_live_network():
    layer = build_security_audit_layer()
    assert all(not f["live_network_used"] for f in layer["findings"])


def test_ais6_no_automatic_patching():
    layer = build_security_audit_layer()
    assert all(not f["automatic_patch_performed"] for f in layer["findings"])


def test_ais6_findings_create_remediation_tasks_only():
    layer = build_security_audit_layer()
    assert all(f["findings_create_remediation_tasks_only"] for f in layer["findings"])


def test_ais6_no_authority_grant():
    layer = build_security_audit_layer()
    assert all(not f["authority_granted"] for f in layer["findings"])


def test_ais6_no_tool_authorization():
    layer = build_security_audit_layer()
    assert all(not f["tools_authorized"] for f in layer["findings"])


def test_ais6_replay_preserves_security_hashes():
    layer = build_security_audit_layer()
    replay = replay_security_audit_layer(layer["findings"], layer["manifest"])
    assert replay["replay_preserves_security_hashes"] is True


def test_ais6_replay_rejects_mutated_hash():
    layer = build_security_audit_layer()
    mutated = [dict(f) for f in layer["findings"]]
    mutated[0]["record_hash"] = "mutated"
    replay = replay_security_audit_layer(mutated, layer["manifest"])
    assert replay["replay_preserves_security_hashes"] is False


def test_ais6_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_ais6_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_ais6_rejects_exploit_payload_laundering():
    finding = build_security_finding(finding_id="sec-bad", finding_type="staged_secret_pattern", surface="x")
    finding["exploit_payload_included"] = True
    with pytest.raises(ValueError):
        validate_security_finding(finding)


def test_ais6_gate_passes_on_full_summary():
    assert validate_ais6_gate(_gate_summary())["ok"] is True


def test_ais6_gate_refuses_live_network():
    assert validate_ais6_gate(_gate_summary(live_network_used=True))["ok"] is False


def test_ais6_gate_refuses_authority():
    assert validate_ais6_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_ais6_gate_refuses_exploit_payload():
    assert validate_ais6_gate(_gate_summary(exploit_payload_included=True))["ok"] is False
