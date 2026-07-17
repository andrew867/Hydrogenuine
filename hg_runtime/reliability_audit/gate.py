"""LHRE-05 / CAGI-58 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.reliability_audit.schemas import VERDICT_RED


def validate_lhre05_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "lhre04_green": "lhre04_not_green",
        "phase_records_written": "records_required",
        "findings_written": "findings_required",
        "cross_phase_consistency_checked": "consistency_required",
        "all_records_valid": "records_must_be_valid",
        "no_critical_findings": "no_critical_allowed",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_audit_authority_tripwire": "reject_audit_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_audit_authority_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "deployment_certified", "tool_authorized", "authority_granted",
        "live_effect_created", "agi_claimed", "auto_remediated",
        "audit_treated_as_certification", "web_browse_performed",
        "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
