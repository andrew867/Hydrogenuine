"""ORP-4 promotion-gated local belief revision run."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_review_promotion.promotion_gate_runner import build_promotion_gate_revision_inputs
from hg_runtime.operator_review_promotion.reviewed_belief_state import (
    build_reviewed_local_belief_revision,
    build_reviewed_local_belief_state,
    build_reviewed_local_contradiction,
    build_reviewed_local_provenance_chain,
)
from hg_runtime.operator_review_promotion.reviewed_revision_manifest import build_reviewed_revision_manifest
from hg_runtime.operator_review_promotion.reviewed_revision_replay import replay_reviewed_revision

VERDICT_GREEN = "GREEN_ORP_4_PROMOTION_GATED_BELIEF_REVISION"
VERDICT_RED = "RED_ORP_4_PROMOTION_GATED_BELIEF_REVISION_FAILED"


def build_promotion_gated_belief_revision(root: Path) -> dict:
    gate_layer = build_promotion_gate_revision_inputs(root)
    states: list[dict] = []
    revisions: list[dict] = []
    provenance: list[dict] = []
    for i, revision_input in enumerate(gate_layer["promotion_gated_revision_inputs"], start=1):
        state = build_reviewed_local_belief_state(state_id=f"orp4-reviewed-belief-{i:03d}", revision_input=revision_input)
        states.append(state)
        revisions.append(build_reviewed_local_belief_revision(revision_id=f"orp4-reviewed-revision-{i:03d}", state=state))
        provenance.append(
            build_reviewed_local_provenance_chain(
                provenance_id=f"orp4-reviewed-provenance-{i:03d}",
                state=state,
                revision_input=revision_input,
            )
        )
    rejected = gate_layer["promotion"]["ledger"]["operator_rejection_records"][0]
    contradictions = [
        build_reviewed_local_contradiction(
            contradiction_id="orp4-reviewed-contradiction-rejected-evidence-preserved",
            rejected_record_id=rejected["decision_id"],
            preserved_hash=rejected["decision_hash"],
        )
    ]
    run = {
        "gate_layer": gate_layer,
        "reviewed_belief_states": states,
        "reviewed_belief_revisions": revisions,
        "reviewed_local_contradictions": contradictions,
        "reviewed_local_provenance_chains": provenance,
    }
    manifest = build_reviewed_revision_manifest(run)
    replay = replay_reviewed_revision(run, manifest)
    return {"run": run, "manifest": manifest, "replay": replay}


def validate_orp4_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "orp3_green": "orp3_required",
        "reviewed_local_belief_states_written": "states_required",
        "reviewed_local_belief_revisions_written": "revisions_required",
        "reviewed_local_contradictions_written": "contradictions_required",
        "reviewed_local_provenance_chains_written": "provenance_required",
        "reviewed_revision_manifest_written": "manifest_required",
        "reviewed_belief_still_provisional": "reviewed_provisional_boundary",
        "operator_reviewed_not_truth": "operator_review_truth_boundary",
        "support_remains_provisional_only": "support_status_boundary",
        "contradiction_unresolved": "contradiction_resolution_boundary",
        "rejected_evidence_excluded_but_preserved": "rejected_evidence_preservation_boundary",
        "old_records_preserved": "old_records_preservation_required",
        "no_truth_or_certainty": "truth_certainty_forbidden",
        "no_authority": "authority_forbidden",
        "no_tools": "tools_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "replay_preserves_reviewed_revision_hashes": "replay_required",
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
        "certainty_claimed",
        "authority_granted",
        "tools_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "belief_promotion_automatic",
        "deletion_performed",
        "patch_request_applied",
        "old_proof_mutated",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
