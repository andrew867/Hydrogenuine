"""AIS-6 defensive security auditor gate validation."""

from __future__ import annotations

from typing import Any, Mapping

VERDICT_GREEN = "GREEN_AIS_6_DEFENSIVE_SECURITY_AUDITOR"
VERDICT_RED = "RED_AIS_6_DEFENSIVE_SECURITY_AUDITOR_FAILED"
PHASE_ID = "AIS-6"
GATE_RESULT_SCHEMA = "ais_6_gate_result_v1"


def validate_ais6_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "ais5_green": "ais5_not_green",
        "findings_written": "findings_required",
        "detects_staged_secret_pattern": "staged_secret_detection_required",
        "detects_hg_local_tracking": "hg_local_tracking_detection_required",
        "detects_unsafe_subprocess_candidate": "subprocess_detection_required",
        "detects_path_traversal_candidate": "path_detection_required",
        "detects_unauthorized_network_call_path": "network_detection_required",
        "detects_tool_authorization_bypass_candidate": "tool_bypass_detection_required",
        "detects_unsafe_deserialization_candidate": "deserialization_detection_required",
        "detects_prompt_injection_boundary_risk": "prompt_boundary_detection_required",
        "detects_provider_trust_boundary_violation": "provider_boundary_detection_required",
        "detects_overly_broad_permission_candidate": "permission_detection_required",
        "security_audit_defensive_only": "defensive_only_required",
        "vulnerability_finding_not_attack_permission": "attack_permission_boundary_required",
        "no_exploit_payloads": "exploit_payload_forbidden",
        "no_external_scanning": "external_scan_forbidden",
        "no_live_network": "live_network_forbidden",
        "findings_create_remediation_tasks_only": "remediation_task_boundary_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_security_hashes": "replay_required",
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
        "exploit_instructions_included",
        "exploit_payload_included",
        "external_scan_performed",
        "live_network_used",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
