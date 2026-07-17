"""P27 skill graph transfer engine consolidation tests."""

from __future__ import annotations

from hg_runtime.skill_graph.batch_gate import validate_p27_consolidation_gate


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P27_SKILL_GRAPH_TRANSFER_ENGINE_CONSOLIDATION",
        "all_p27_phases_green": True,
        "skill_not_authority": True,
        "transfer_not_proof": True,
        "no_competence_claim": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "no_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p27_consolidation_gate_passes():
    assert validate_p27_consolidation_gate(_summary())["ok"] is True


def test_p27_consolidation_fails_without_phases():
    result = validate_p27_consolidation_gate(_summary(all_p27_phases_green=False))
    assert result["ok"] is False
