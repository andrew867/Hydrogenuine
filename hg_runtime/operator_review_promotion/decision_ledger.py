"""ORP-1 append-only operator review decision ledger."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_review_promotion.decision_loader import load_operator_review_inputs
from hg_runtime.operator_review_promotion.decision_replay import replay_decision_ledger
from hg_runtime.operator_review_promotion.decision_writer import (
    build_decisions_from_tasks,
    build_deferral_records,
    build_operator_review_manifest,
    build_rejection_records,
    build_review_links,
)

VERDICT_GREEN = "GREEN_ORP_1_OPERATOR_REVIEW_DECISION_LEDGER"
VERDICT_RED = "RED_ORP_1_OPERATOR_REVIEW_DECISION_LEDGER_FAILED"


def build_operator_review_decision_ledger(root: Path) -> dict:
    inputs = load_operator_review_inputs(root)
    decisions = build_decisions_from_tasks(inputs["leb5_review_tasks"])
    links = build_review_links(decisions)
    rejections = build_rejection_records(decisions)
    deferrals = build_deferral_records(decisions)
    manifest = build_operator_review_manifest(decisions=decisions, links=links, inputs=inputs)
    replay = replay_decision_ledger(decisions, links, rejections, deferrals, manifest)
    return {
        "inputs": inputs,
        "decisions": decisions,
        "reviewed_evidence_links": links,
        "operator_rejection_records": rejections,
        "operator_deferral_records": deferrals,
        "manifest": manifest,
        "replay": replay,
    }


def validate_orp1_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "leb5_inputs_loaded": "leb5_inputs_required",
        "leb6_inputs_loaded": "leb6_inputs_required",
        "leb7_inputs_loaded": "leb7_inputs_required",
        "operator_review_decisions_written": "decisions_required",
        "operator_review_manifest_written": "manifest_required",
        "reviewed_evidence_links_written": "reviewed_links_required",
        "operator_rejection_records_written": "rejections_required",
        "operator_deferral_records_written": "deferrals_required",
        "ledger_is_append_only": "append_only_required",
        "original_evidence_preserved": "original_evidence_preservation_required",
        "approval_does_not_prove": "approval_truth_boundary",
        "approval_does_not_authorize_action": "approval_action_boundary",
        "approval_does_not_authorize_tool": "approval_tool_boundary",
        "approval_does_not_authorize_web_or_provider": "approval_web_provider_boundary",
        "rejection_does_not_delete": "rejection_deletion_boundary",
        "deferral_remains_open": "deferral_open_required",
        "replay_preserves_ledger_hashes": "replay_required",
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
        "web_authorized",
        "providers_authorized",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "belief_promotion_automatic",
        "belief_promoted",
        "deletion_performed",
        "patch_request_applied",
        "arbitrary_file_ingestion_enabled",
        "pdf_ingestion_enabled",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
