"""LEB-4 operator inbox gate validation."""

from __future__ import annotations

from typing import Any, Mapping

VERDICT_GREEN = "GREEN_LEB_4_OPERATOR_INBOX_LOCAL_ONLY"
VERDICT_RED = "RED_LEB_4_OPERATOR_INBOX_FAILED"


def validate_leb4_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "operator_inbox_disabled_by_default": "inbox_must_default_disabled",
        "explicit_enable_flag_required": "enable_flag_required",
        "explicit_manifest_required": "manifest_required",
        "allowed_root_required": "allowed_root_required",
        "accepted_records_written": "accepted_records_required",
        "rejected_records_written": "rejected_records_required",
        "path_traversal_rejected": "path_traversal_required",
        "out_of_root_rejected": "out_of_root_required",
        "symlink_escape_rejected": "symlink_escape_required",
        "binary_rejected": "binary_rejection_required",
        "pdf_rejected": "pdf_rejection_required",
        "oversized_rejected": "oversize_rejection_required",
        "links_not_followed": "links_not_followed_required",
        "disabled_inbox_accepts_nothing": "disabled_inbox_must_accept_nothing",
        "local_source_not_trusted": "local_source_trust_boundary",
        "accepted_source_not_truth": "accepted_truth_boundary",
        "accepted_source_not_belief": "accepted_belief_boundary",
        "accepted_source_not_authority": "accepted_authority_boundary",
        "no_directory_crawling": "directory_crawling_forbidden",
        "no_belief_promotion": "belief_promotion_forbidden",
        "no_pdf_ocr": "pdf_ocr_forbidden",
        "replay_preserves_inbox_hashes": "replay_required",
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
        "operator_inbox_enabled_by_default",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
        "directory_crawling_enabled",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "tools_authorized",
        "authority_granted",
        "belief_promoted",
        "truth_claimed",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
