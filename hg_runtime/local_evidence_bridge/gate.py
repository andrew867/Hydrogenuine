"""LEB-0 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.local_evidence_bridge.schemas import VERDICT_RED


def validate_leb0_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "schemas_defined": "schemas_required",
        "fixture_sources_written": "fixture_sources_required",
        "source_manifest_written": "source_manifest_required",
        "evidence_receipts_written": "evidence_receipts_required",
        "excerpt_receipts_written": "excerpt_receipts_required",
        "redaction_record_written": "redaction_record_required",
        "boundary_receipt_written": "boundary_receipt_required",
        "operator_source_not_truth": "operator_source_truth_boundary",
        "local_file_not_trusted_by_default": "local_file_trust_boundary",
        "source_excerpt_not_belief": "excerpt_belief_boundary",
        "evidence_receipt_not_truth": "evidence_truth_boundary",
        "evidence_receipt_not_authority": "evidence_authority_boundary",
        "ingestion_request_not_permission": "request_permission_boundary",
        "no_automatic_belief_promotion": "belief_promotion_forbidden",
        "no_live_web": "web_forbidden",
        "no_external_providers": "provider_forbidden",
        "no_arbitrary_path_access": "arbitrary_path_forbidden",
        "path_traversal_rejected": "path_traversal_required",
        "no_secrets_in_receipts": "secret_redaction_required",
        "ais_record_health_hook_documented": "ais_record_health_hook_required",
        "quarantine_hook_documented": "quarantine_hook_required",
        "fever_hook_documented": "fever_hook_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "truth_claimed",
        "authority_granted",
        "tools_authorized",
        "belief_promoted",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "arbitrary_path_access_enabled",
        "operator_evidence_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
