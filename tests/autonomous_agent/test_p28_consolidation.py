"""P28 domain pack runtime consolidation tests."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.gate import validate_p28_consolidation_gate


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P28_DOMAIN_PACK_RUNTIME_CONSOLIDATION",
        "all_p28_phases_green": True,
        "domain_pack_not_permission": True,
        "domain_label_not_expertise": True,
        "readiness_not_deployment": True,
        "skill_link_not_authority": True,
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


def test_p28_consolidation_gate_passes():
    assert validate_p28_consolidation_gate(_summary())["ok"] is True


def test_p28_consolidation_fails_without_phases():
    result = validate_p28_consolidation_gate(_summary(all_p28_phases_green=False))
    assert result["ok"] is False
