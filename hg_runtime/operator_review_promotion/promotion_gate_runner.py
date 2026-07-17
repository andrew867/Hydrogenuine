"""ORP-3 promotion gate to local belief revision inputs."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_review_promotion.promotion_gate import build_promotion_gate_result
from hg_runtime.operator_review_promotion.promotion_gate_replay import replay_promotion_gate
from hg_runtime.operator_review_promotion.promotion_request_builder import build_evidence_promotion_requests
from hg_runtime.operator_review_promotion.promotion_to_revision_input import build_promotion_gated_revision_input
from hg_runtime.operator_review_promotion.revision_input_writer import build_promotion_gate_manifest

VERDICT_GREEN = "GREEN_ORP_3_PROMOTION_GATE_REVISION_INPUTS"
VERDICT_RED = "RED_ORP_3_PROMOTION_GATE_REVISION_INPUTS_FAILED"


def build_promotion_gate_revision_inputs(root: Path) -> dict:
    promotion = build_evidence_promotion_requests(root)
    gate_results = [
        build_promotion_gate_result(gate_result_id=f"orp3-promotion-gate-{i:03d}", request=request, passed=True)
        for i, request in enumerate(promotion["promotion_requests"], start=1)
    ]
    revision_inputs = [
        build_promotion_gated_revision_input(input_id=f"orp3-revision-input-{i:03d}", gate_result=gate_result, request=request)
        for i, (gate_result, request) in enumerate(zip(gate_results, promotion["promotion_requests"], strict=True), start=1)
    ]
    manifest = build_promotion_gate_manifest(
        request_manifest=promotion["manifest"],
        gate_results=gate_results,
        revision_inputs=revision_inputs,
    )
    replay = replay_promotion_gate(gate_results, revision_inputs, manifest)
    return {
        "promotion": promotion,
        "promotion_gate_results": gate_results,
        "promotion_gated_revision_inputs": revision_inputs,
        "manifest": manifest,
        "replay": replay,
    }


def validate_orp3_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "orp2_green": "orp2_required",
        "promotion_gate_results_written": "gate_results_required",
        "promotion_gated_revision_inputs_written": "revision_inputs_required",
        "promotion_gate_manifest_written": "manifest_required",
        "gate_pass_not_truth": "gate_truth_boundary",
        "gate_pass_not_certainty": "gate_certainty_boundary",
        "gate_pass_not_action_permission": "gate_action_boundary",
        "gate_fail_not_deletion": "gate_fail_deletion_boundary",
        "revision_input_not_belief_state": "revision_input_belief_boundary",
        "no_old_proof_mutation": "old_proof_mutation_forbidden",
        "no_automatic_belief_promotion": "automatic_promotion_forbidden",
        "no_authority": "authority_forbidden",
        "no_tools": "tools_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "replay_preserves_gate_hashes": "replay_required",
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
        "evidence_treated_as_truth",
        "operator_review_treated_as_truth",
        "truth_claimed",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "belief_promoted",
        "belief_promotion_automatic",
        "deletion_performed",
        "patch_request_applied",
        "old_proof_mutated",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
