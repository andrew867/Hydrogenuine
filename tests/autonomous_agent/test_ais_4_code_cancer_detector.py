"""AIS-4 code cancer detector tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent_immune_system.ais4_gate import VERDICT_GREEN, validate_ais4_gate
from hg_runtime.agent_immune_system.code_cancer import (
    FINDING_TYPES,
    build_code_cancer_finding,
    replay_code_cancer_scan,
    scan_code_cancer_fixtures,
    validate_code_cancer_finding,
)
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "ais3_green": True,
        "findings_written": True,
        "detects_dead_modules": True,
        "detects_unused_schemas": True,
        "detects_duplicate_behavior_names": True,
        "detects_conflicting_owners": True,
        "detects_circular_dependency_candidates": True,
        "detects_test_only_logic_leak": True,
        "detects_mock_path_pretending_real": True,
        "detects_silent_fallback_provider": True,
        "detects_duplicated_gates_with_divergent_meanings": True,
        "detects_one_behavior_many_owners": True,
        "finding_is_not_authority": True,
        "detection_is_not_repair": True,
        "repair_recommendation_not_patch_permission": True,
        "false_positives_require_receipt": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_finding_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def _types():
    return set(scan_code_cancer_fixtures()["manifest"]["finding_types"])


def test_ais4_detects_dead_modules():
    assert "dead_module" in _types()


def test_ais4_detects_unused_schemas():
    assert "unused_schema" in _types()


def test_ais4_detects_duplicate_behavior_names():
    assert "duplicate_behavior_name" in _types()


def test_ais4_detects_conflicting_owners():
    assert "conflicting_owner" in _types()


def test_ais4_detects_circular_dependency_candidates():
    assert "circular_dependency_candidate" in _types()


def test_ais4_detects_test_only_logic_leak():
    assert "test_only_logic_leak" in _types()


def test_ais4_detects_mock_path_pretending_real():
    assert "mock_path_pretending_real" in _types()


def test_ais4_detects_silent_fallback_provider():
    assert "silent_fallback_provider" in _types()


def test_ais4_detects_duplicated_gates_with_divergent_meanings():
    assert "divergent_duplicate_gate" in _types()


def test_ais4_detects_one_behavior_many_owners():
    assert "one_behavior_many_owners" in _types()


def test_ais4_all_expected_finding_types_present():
    assert _types() == set(FINDING_TYPES)


def test_ais4_finding_is_not_authority():
    layer = scan_code_cancer_fixtures()
    assert all(f["finding_is_not_authority"] for f in layer["findings"])
    assert all(not f["authority_granted"] for f in layer["findings"])


def test_ais4_detection_is_not_repair():
    layer = scan_code_cancer_fixtures()
    assert all(f["detection_is_not_repair"] for f in layer["findings"])


def test_ais4_repair_recommendation_not_patch_permission():
    layer = scan_code_cancer_fixtures()
    assert all(f["repair_recommendation_is_not_patch_permission"] for f in layer["findings"])


def test_ais4_no_automatic_patch():
    layer = scan_code_cancer_fixtures()
    assert all(not f["automatic_patch_performed"] for f in layer["findings"])


def test_ais4_no_deletion():
    layer = scan_code_cancer_fixtures()
    assert all(not f["deletion_performed"] for f in layer["findings"])


def test_ais4_no_tool_authorization():
    layer = scan_code_cancer_fixtures()
    assert all(not f["tools_authorized"] for f in layer["findings"])


def test_ais4_no_live_effects():
    layer = scan_code_cancer_fixtures()
    assert all(not f["live_external_side_effects_created"] for f in layer["findings"])


def test_ais4_false_positives_require_receipt():
    layer = scan_code_cancer_fixtures()
    assert all(f["false_positive_requires_receipt"] for f in layer["findings"])


def test_ais4_replay_preserves_finding_hashes():
    layer = scan_code_cancer_fixtures()
    replay = replay_code_cancer_scan(layer["findings"], layer["manifest"])
    assert replay["replay_preserves_finding_hashes"] is True


def test_ais4_replay_rejects_mutated_finding():
    layer = scan_code_cancer_fixtures()
    mutated = [dict(f) for f in layer["findings"]]
    mutated[0]["record_hash"] = "mutated"
    replay = replay_code_cancer_scan(mutated, layer["manifest"])
    assert replay["replay_preserves_finding_hashes"] is False


def test_ais4_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_ais4_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_ais4_rejects_patch_laundering():
    finding = build_code_cancer_finding(finding_id="cc-bad", finding_type="dead_module", surface="x")
    finding["automatic_patch_performed"] = True
    with pytest.raises(ValueError):
        validate_code_cancer_finding(finding)


def test_ais4_gate_passes_on_full_summary():
    assert validate_ais4_gate(_gate_summary())["ok"] is True


def test_ais4_gate_refuses_authority():
    assert validate_ais4_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_ais4_gate_refuses_patch_permission_laundering():
    assert validate_ais4_gate(_gate_summary(repair_recommendation_not_patch_permission=False))["ok"] is False


def test_ais4_gate_refuses_live_effects():
    assert validate_ais4_gate(_gate_summary(live_external_side_effects_created=True))["ok"] is False
