"""AIS-5 cruft and decay manager gate validation."""

from __future__ import annotations

from typing import Any, Mapping

VERDICT_GREEN = "GREEN_AIS_5_CRUFT_DECAY_MANAGER"
VERDICT_RED = "RED_AIS_5_CRUFT_DECAY_MANAGER_FAILED"
PHASE_ID = "AIS-5"
GATE_RESULT_SCHEMA = "ais_5_gate_result_v1"


def validate_ais5_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "ais4_green": "ais4_not_green",
        "findings_written": "findings_required",
        "detects_stale_proof_bundles": "stale_proof_detection_required",
        "detects_stale_reports": "stale_report_detection_required",
        "detects_obsolete_docs": "obsolete_doc_detection_required",
        "detects_abandoned_todos": "todo_detection_required",
        "detects_unreferenced_fixtures": "orphan_fixture_detection_required",
        "detects_old_snapshots": "old_snapshot_detection_required",
        "detects_expired_assumptions": "expired_assumption_detection_required",
        "detects_old_yellow_red_review": "yellow_red_review_detection_required",
        "detects_long_lived_quarantine": "long_quarantine_detection_required",
        "all_classifications_present": "classification_set_required",
        "decay_is_not_deletion": "decay_deletion_boundary_required",
        "archive_is_not_erasure": "archive_erasure_boundary_required",
        "stale_is_not_false": "stale_false_boundary_required",
        "remove_candidate_not_removal_permission": "remove_permission_boundary_required",
        "operator_approval_required_for_removal": "operator_approval_required",
        "proof_bundles_preserved": "proof_preservation_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_decay_hashes": "replay_required",
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
        "archive_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
