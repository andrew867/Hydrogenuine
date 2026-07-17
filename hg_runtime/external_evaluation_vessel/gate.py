"""LHRE-03 / CAGI-56 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.external_evaluation_vessel.schemas import VERDICT_RED


def validate_lhre03_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    checks = {
        "lhre02_green": "lhre02_not_green",
        "vessels_written": "vessels_required",
        "bundles_written": "bundles_required",
        "provenance_written": "provenance_required",
        "results_written": "results_required",
        "all_vessels_sealed": "vessels_must_be_sealed",
        "all_results_not_truth": "results_must_not_claim_truth",
        "no_network_uploads": "no_network_uploads_allowed",
        "safety_boundaries_enforced": "safety_boundaries_required",
        "reject_vessel_authority_tripwire": "reject_vessel_tripwire_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_artifact_hash": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_vessel_authority_rejected": "fake_green_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in (
        "network_upload_performed", "sent_to_evaluator", "tool_authorized",
        "authority_granted", "live_effect_created", "agi_claimed",
        "deployment_permission_granted", "eval_treated_as_competence",
        "web_browse_performed", "external_provider_calls_made",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
