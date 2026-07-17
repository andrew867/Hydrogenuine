"""P26 experience-ledger gap reconciliation gate validator."""

from __future__ import annotations

from hg_runtime.generalist_gap_reconciliation.schemas import VERDICT_RED_P26_GAP


def validate_p26_gap_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "acceptance_criteria_written": "criteria_required",
        "existing_artifact_map_written": "artifact_map_required",
        "gap_records_written": "gap_records_required",
        "recommendation_records_written": "recommendations_required",
        "all_gap_statuses_exercised": "gap_statuses_required",
        "requires_exact_p26_present": "requires_exact_p26_required",
        "gap_analysis_not_completion": "gap_completion_boundary",
        "partial_not_green": "partial_green_boundary",
        "existing_artifacts_do_not_auto_complete": "auto_complete_boundary",
        "p26_not_marked_complete": "p26_completion_boundary",
        "no_authority_change": "authority_change_boundary",
        "no_new_ingestion": "new_ingestion_boundary",
        "no_belief_promotion": "belief_promotion_boundary",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_manifest_hash": "manifest_replay_required",
        "replay_preserves_gap_hashes": "gap_replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "gap_analysis_is_completion",
        "partial_satisfaction_is_green",
        "existing_artifact_auto_completes_p26",
        "p26_marked_complete",
        "authority_changed",
        "authority_granted",
        "tools_authorized",
        "new_ingestion_enabled",
        "arbitrary_file_ingestion_enabled",
        "pdf_ocr_enabled",
        "html_parsing_enabled",
        "belief_promoted",
        "belief_promotion_automatic",
        "deletion_performed",
        "patch_request_applied",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_P26_GAP, "failures": failures}
