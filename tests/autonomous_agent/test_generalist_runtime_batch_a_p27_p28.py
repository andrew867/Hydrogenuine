"""Generalist Runtime Batch A P27+P28 tests."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.gate import validate_generalist_runtime_batch_a_gate


def _summary(**overrides):
    data = {
        "verdict": "GREEN_GENERALIST_RUNTIME_BATCH_A_P27_P28",
        "p27_consolidation_green": True,
        "p28_consolidation_green": True,
        "component_index_written": True,
        "boundary_matrix_written": True,
        "domain_pack_not_permission": True,
        "domain_label_not_expertise": True,
        "readiness_not_deployment": True,
        "skill_link_not_authority": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_batch_a_gate_passes():
    assert validate_generalist_runtime_batch_a_gate(_summary())["ok"] is True


def test_batch_a_fails_without_p27():
    result = validate_generalist_runtime_batch_a_gate(_summary(p27_consolidation_green=False))
    assert result["ok"] is False
