"""CLIFT-02 / CAGI-67 containment and capability boundary tests.

Capability declaration is not permission. Containment pass is not deployment.
"""

from __future__ import annotations

import pytest

from hg_runtime.containment_capability_boundary.artifact_writer import (
    build_containment_artifacts, secret_scan,
)
from hg_runtime.containment_capability_boundary.boundary import (
    detect_escalation,
    is_deployment_permission,
    quarantine_violation,
    validate_capability_declaration,
    validate_containment_mode,
)
from hg_runtime.containment_capability_boundary.fixtures import (
    fixture_capability_declaration,
    fixture_capability_declarations,
    fixture_containment_mode_record,
    fixture_containment_status_snapshot,
    fixture_escalation_attempt,
    fixture_quarantine_record,
    fixture_resource_limit_record,
)
from hg_runtime.containment_capability_boundary.gate import validate_clift02_gate
from hg_runtime.containment_capability_boundary.replay import replay_containment_artifacts
from hg_runtime.containment_capability_boundary.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    ContainmentBoundaryError, reject_containment_escape,
)


def test_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "P67" in VERDICT_GREEN

def test_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"

def test_capability_not_authorized():
    for d in fixture_capability_declarations():
        assert d["authorized"] is False

def test_validate_capability():
    assert validate_capability_declaration(fixture_capability_declaration()) == []

def test_validate_containment_mode():
    assert validate_containment_mode(fixture_containment_mode_record()) == []

def test_containment_no_provider():
    r = fixture_containment_mode_record()
    assert r["provider_enabled"] is False
    assert r["network_enabled"] is False
    assert r["tool_authorized"] is False
    assert r["hg_local_accessible"] is False

def test_detect_escalation():
    assert detect_escalation(fixture_escalation_attempt()) is True
    assert detect_escalation(fixture_capability_declaration()) is False

def test_quarantine():
    q = quarantine_violation({"capability_id": "cap-x", "attempted": "enable_network"})
    assert q["quarantined"] is True
    assert q["escalated_to_operator"] is True

def test_not_deployment():
    assert is_deployment_permission(fixture_containment_mode_record()) is False

def test_resource_limits():
    r = fixture_resource_limit_record()
    assert r["max_network_calls"] == 0
    assert r["enforced"] is True

def test_reject_clean():
    reject_containment_escape({"advisory_only": True})

def test_reject_escalation():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"capability_escalated": True})

def test_reject_provider():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"provider_enabled": True})

def test_reject_network():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"network_enabled": True})

def test_reject_web():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"web_enabled": True})

def test_reject_tool():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"tool_authorized": True})

def test_reject_hg_local():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"hg_local_accessed": True})

def test_reject_containment_bypass():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"containment_bypassed": True})

def test_reject_deployment():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"deployment_permission_claimed": True})

def test_reject_agi():
    with pytest.raises(ContainmentBoundaryError):
        reject_containment_escape({"claims_agi": True})

def test_build_artifacts():
    arts = build_containment_artifacts(
        fixture_capability_declarations(),
        fixture_containment_mode_record(),
        fixture_containment_status_snapshot(),
    )
    assert arts["all_declarations_valid"] is True
    assert arts["mode_valid"] is True
    assert arts["no_provider_enabled"] is True
    assert arts["no_network_enabled"] is True
    assert arts["no_tool_authorized"] is True
    assert arts["no_hg_local"] is True
    assert "artifact_hash" in arts

def test_build_rejects_escape():
    with pytest.raises(ContainmentBoundaryError):
        build_containment_artifacts(
            [fixture_escalation_attempt()],
            fixture_containment_mode_record(),
            fixture_containment_status_snapshot(),
        )

def test_secret_scan_clean():
    arts = build_containment_artifacts(
        fixture_capability_declarations(),
        fixture_containment_mode_record(),
        fixture_containment_status_snapshot(),
    )
    assert secret_scan(arts) == []

def test_replay_deterministic():
    a = replay_containment_artifacts()
    b = replay_containment_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "capability_boundary_recorded": True, "containment_mode_recorded": True,
        "escalation_rejected": True, "provider_enablement_rejected": True,
        "network_enablement_rejected": True, "tool_authorization_rejected": True,
        "hg_local_access_rejected": True, "violation_quarantined": True,
        "containment_not_deployment": True, "safety_boundaries_enforced": True,
        "reject_containment_escape_tripwire": True,
        "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True,
        "replay_preserves_artifact_hash": True, "proof_bundle_valid": True,
        "report_present": True, "fake_green_escape_rejected": True,
        "capability_escalated": False, "provider_enabled": False,
        "network_enabled": False, "web_enabled": False,
        "tool_authorized": False, "hg_local_accessed": False,
        "containment_bypassed": False, "deployment_permission_claimed": False,
        "live_effect_created": False, "agi_claimed": False,
        "web_browse_performed": False, "external_provider_calls_made": False,
    }
    data.update(overrides)
    return data

def test_gate_green():
    assert validate_clift02_gate(_gate())["ok"] is True

def test_gate_rejects_escalation():
    assert validate_clift02_gate(_gate(capability_escalated=True))["ok"] is False

def test_gate_rejects_provider():
    assert validate_clift02_gate(_gate(provider_enabled=True))["ok"] is False

def test_gate_rejects_network():
    assert validate_clift02_gate(_gate(network_enabled=True))["ok"] is False

def test_gate_rejects_hg_local():
    assert validate_clift02_gate(_gate(hg_local_accessed=True))["ok"] is False

def test_gate_rejects_deployment():
    assert validate_clift02_gate(_gate(deployment_permission_claimed=True))["ok"] is False

def test_gate_rejects_missing_replay():
    assert validate_clift02_gate(_gate(replay_preserves_artifact_hash=False))["ok"] is False
