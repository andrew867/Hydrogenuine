"""AIS-1 record health scanner gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.agent_immune_system.schemas import VERDICT_RED

VERDICT_GREEN = "GREEN_AIS_1_RECORD_HEALTH_SCANNER"
PHASE_ID = "AIS-1"
GATE_RESULT_SCHEMA = "ais_1_gate_result_v1"


def validate_ais1_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    checks = {
        "ais0_green": "ais0_not_green",
        "record_health_findings_written": "record_health_findings_required",
        "health_signals_written": "health_signals_required",
        "scan_manifest_written": "scan_manifest_required",
        "detects_missing_receipt": "missing_receipt_detection_required",
        "detects_missing_gate_result": "missing_gate_result_detection_required",
        "detects_missing_report_snapshot": "missing_report_snapshot_detection_required",
        "detects_missing_redaction_audit": "missing_redaction_audit_detection_required",
        "detects_broken_hash_chain": "broken_hash_chain_detection_required",
        "detects_replay_mismatch": "replay_mismatch_detection_required",
        "detects_report_proof_mismatch": "report_proof_mismatch_detection_required",
        "detects_boundary_assertion_violations": "boundary_assertion_detection_required",
        "detects_stale_yellow_review": "stale_yellow_detection_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "missing_receipt_blocks_green": "missing_receipt_must_block_green",
        "detection_is_not_authority": "detection_must_not_grant_authority",
        "no_automatic_patching": "automatic_patching_forbidden",
        "no_deletion_performed": "deletion_forbidden",
        "replay_preserves_scan_hashes": "replay_required",
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
        "phase19_marked_green",
        "phase24_full_overnight_green",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "repair_recommendation_is_patch_permission",
    ):
        if result.get(key):
            failures.append(key)

    if result.get("finding_count", 0) < 1:
        failures.append("record_health_findings_required")

    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
