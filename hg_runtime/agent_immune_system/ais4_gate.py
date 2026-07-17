"""AIS-4 code cancer detector gate validation."""

from __future__ import annotations

from typing import Any, Mapping

VERDICT_GREEN = "GREEN_AIS_4_CODE_CANCER_DETECTOR"
VERDICT_RED = "RED_AIS_4_CODE_CANCER_DETECTOR_FAILED"
PHASE_ID = "AIS-4"
GATE_RESULT_SCHEMA = "ais_4_gate_result_v1"


def validate_ais4_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "ais3_green": "ais3_not_green",
        "findings_written": "findings_required",
        "detects_dead_modules": "dead_module_detection_required",
        "detects_unused_schemas": "unused_schema_detection_required",
        "detects_duplicate_behavior_names": "duplicate_behavior_detection_required",
        "detects_conflicting_owners": "owner_conflict_detection_required",
        "detects_circular_dependency_candidates": "circular_dependency_detection_required",
        "detects_test_only_logic_leak": "test_logic_leak_detection_required",
        "detects_mock_path_pretending_real": "mock_path_detection_required",
        "detects_silent_fallback_provider": "fallback_detection_required",
        "detects_duplicated_gates_with_divergent_meanings": "gate_drift_detection_required",
        "detects_one_behavior_many_owners": "many_owners_detection_required",
        "finding_is_not_authority": "finding_authority_boundary_required",
        "detection_is_not_repair": "detection_repair_boundary_required",
        "repair_recommendation_not_patch_permission": "patch_permission_boundary_required",
        "false_positives_require_receipt": "false_positive_receipt_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_finding_hashes": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "authority_granted",
        "tools_authorized",
        "automatic_patching_allowed",
        "deletion_performed",
        "live_external_side_effects_created",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
