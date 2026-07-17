"""ORP-0 gate validation."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import VERDICT_RED_ORP0


def validate_orp0_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "schemas_declared": "schemas_required",
        "decision_statuses_declared": "decision_statuses_required",
        "operator_review_decisions_written": "decisions_required",
        "operator_review_manifest_written": "manifest_required",
        "promotion_policy_receipt_written": "policy_required",
        "promotion_request_written": "promotion_request_required",
        "promotion_gate_result_written": "promotion_gate_required",
        "reviewed_evidence_link_written": "reviewed_link_required",
        "operator_rejection_record_written": "rejection_record_required",
        "operator_deferral_record_written": "deferral_record_required",
        "operator_review_not_truth": "operator_review_truth_boundary",
        "operator_approval_not_action_permission": "approval_action_boundary",
        "operator_approval_does_not_authorize_tools": "approval_tool_boundary",
        "operator_approval_does_not_authorize_web": "approval_web_boundary",
        "operator_approval_does_not_authorize_providers": "approval_provider_boundary",
        "operator_rejection_not_deletion": "rejection_deletion_boundary",
        "operator_deferral_not_failure": "deferral_failure_boundary",
        "promotion_request_not_promotion": "request_promotion_boundary",
        "promotion_gate_not_truth": "gate_truth_boundary",
        "no_automatic_belief_promotion": "automatic_promotion_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "replay_preserves_review_hashes": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "operator_review_treated_as_truth",
        "evidence_treated_as_truth",
        "authority_granted",
        "tools_authorized",
        "web_authorized",
        "providers_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "belief_promoted",
        "belief_promotion_automatic",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_ORP0, "failures": failures}
