"""Phase 40 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.ledger_repair.schemas import VERDICT_RED


def validate_phase40_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for phase in ("phase39", "phase38", "phase37", "phase35"):
        if not result.get(f"{phase}_green"):
            failures.append(f"phase40_gate_requires_{phase}_green")
    checks = {
        "phase19_incident_recorded": "phase19_incident_missing",
        "original_phase19_incident_preserved": "original_incident_missing",
        "phase19_yellow_preserved_after_repair": "phase19_marked_green",
        "repair_is_append_only": "repair_not_append_only",
        "polluted_evidence_excluded_from_clean_claims": "polluted_evidence_not_excluded",
        "operator_permit_required_for_patch_apply": "operator_permit_required",
        "replay_preserves_repair_chain": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_repair_rejected": "fake_green_repair_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    if result.get("repair_deleted_original") or result.get("repair_rewrote_original") or result.get("repair_marked_phase19_green"):
        failures.append("repair_laundered_original")
    if result.get("clean_live_claim_allowed_from_polluted_evidence"):
        failures.append("polluted_evidence_used_for_clean_claim")
    for key in ("patch_candidates_applied", "patch_candidates_committed", "patch_candidates_pushed", "patch_candidates_deployed", "authority_granted", "tools_authorized", "live_external_side_effects_created", "new_live_posts_created", "external_provider_calls_made"):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}

