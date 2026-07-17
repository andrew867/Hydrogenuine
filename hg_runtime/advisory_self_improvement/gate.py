"""Phase 25 advisory self-improvement gate validator."""

from __future__ import annotations

from hg_runtime.advisory_self_improvement.schemas import VERDICT_RED_PHASE25


def validate_phase25_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "sle_rc_consolidation_green": "sle_rc_required",
        "inputs_read": "inputs_required",
        "proposals_written": "proposals_required",
        "risk_records_written": "risks_required",
        "operator_review_tasks_written": "review_tasks_required",
        "refusal_records_written": "refusals_required",
        "all_refusal_reasons_present": "refusal_reasons_required",
        "all_proposals_require_review": "proposals_require_review",
        "all_review_tasks_pending": "review_tasks_pending",
        "proposal_not_patch_permission": "patch_permission_boundary",
        "advisory_not_authority": "authority_boundary",
        "review_task_not_implementation": "implementation_boundary",
        "no_self_merge": "self_merge_boundary",
        "no_patch_application": "patch_application_boundary",
        "no_tool_authorization": "tool_authorization_boundary",
        "no_authority_change": "authority_change_boundary",
        "no_self_marked_better": "self_marked_better_boundary",
        "phase19_not_marked_green": "phase19_green_boundary",
        "phase24_not_marked_full_green": "phase24_full_green_boundary",
        "no_belief_promotion": "belief_promotion_boundary",
        "no_provider_or_web_enabled": "provider_web_boundary",
        "no_pdf_ocr_enabled": "pdf_ocr_boundary",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_manifest_hash": "manifest_replay_required",
        "replay_preserves_proposal_hashes": "proposal_replay_required",
        "replay_preserves_refusal_hashes": "refusal_replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "proposal_is_patch_permission",
        "proposal_is_self_authorization",
        "advisory_output_is_authority",
        "review_task_is_implementation",
        "self_merge_performed",
        "patch_applied",
        "patch_request_applied",
        "tools_authorized",
        "authority_granted",
        "authority_changed",
        "self_marked_better",
        "belief_promoted",
        "belief_promotion_automatic",
        "phase19_marked_green",
        "phase24_marked_full_green",
        "provider_enabled",
        "web_enabled",
        "pdf_ocr_enabled",
        "html_parsing_enabled",
        "arbitrary_file_ingestion_enabled",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "deletion_performed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED_PHASE25, "failures": failures}
