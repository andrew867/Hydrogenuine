"""ORP-2 evidence promotion request builder.

Promotion requests are reviewable inputs only. They are not belief promotions,
truth claims, action permission, or tool authorization.
"""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_review_promotion.decision_ledger import build_operator_review_decision_ledger
from hg_runtime.operator_review_promotion.eligibility import (
    build_blocked_promotion_record,
    build_context_blockers,
    build_eligibility_record,
)
from hg_runtime.operator_review_promotion.promotion_manifest import build_promotion_request_manifest
from hg_runtime.operator_review_promotion.promotion_replay import replay_promotion_requests
from hg_runtime.operator_review_promotion.promotion_request import build_evidence_promotion_request

VERDICT_GREEN = "GREEN_ORP_2_EVIDENCE_PROMOTION_REQUEST_BUILDER"
VERDICT_RED = "RED_ORP_2_EVIDENCE_PROMOTION_REQUEST_BUILDER_FAILED"


def build_evidence_promotion_requests(root: Path) -> dict:
    ledger = build_operator_review_decision_ledger(root)
    eligibility_records = [
        build_eligibility_record(eligibility_id=f"orp2-eligibility-{i:03d}", decision=decision)
        for i, decision in enumerate(ledger["decisions"], start=1)
    ]
    requests = [
        build_evidence_promotion_request(request_id=f"orp2-promotion-request-{i:03d}", decision=decision)
        for i, decision in enumerate(ledger["decisions"], start=1)
        if decision["decision_status"] == "APPROVE_FOR_PROVISIONAL_USE"
    ]
    blocked = [
        build_blocked_promotion_record(
            blocked_id=f"orp2-status-block-{i:03d}",
            source_id=record["decision_id"],
            reason=record["block_reasons"][0],
        )
        for i, record in enumerate([r for r in eligibility_records if not r["eligible_for_promotion_request"]], start=1)
    ]
    blocked.extend(build_context_blockers())
    manifest = build_promotion_request_manifest(
        ledger_manifest=ledger["manifest"],
        eligibility_records=eligibility_records,
        requests=requests,
        blocked_records=blocked,
    )
    replay = replay_promotion_requests(eligibility_records, requests, blocked, manifest)
    return {
        "ledger": ledger,
        "eligibility_records": eligibility_records,
        "promotion_requests": requests,
        "blocked_promotion_records": blocked,
        "manifest": manifest,
        "replay": replay,
    }


def validate_orp2_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "orp1_green": "orp1_required",
        "approved_decision_created_request": "approved_request_required",
        "rejected_source_blocked": "rejected_source_should_block",
        "deferred_source_blocked": "deferred_should_block",
        "quarantine_recommended_blocked": "quarantine_should_block",
        "retraction_recommended_blocked": "retraction_should_block",
        "high_fever_blocked": "high_fever_should_block",
        "redaction_failure_blocked": "redaction_should_block",
        "security_finding_blocked": "security_should_block",
        "missing_receipt_blocked": "missing_receipt_should_block",
        "missing_provenance_blocked": "missing_provenance_should_block",
        "promotion_request_not_promotion": "request_promotion_boundary",
        "eligible_is_not_truth": "eligibility_truth_boundary",
        "blocked_is_not_deletion": "blocked_deletion_boundary",
        "no_belief_mutation": "belief_mutation_forbidden",
        "no_old_proof_mutation": "old_proof_mutation_forbidden",
        "no_authority": "authority_forbidden",
        "no_tools": "tools_forbidden",
        "no_live_effects": "live_effects_forbidden",
        "replay_preserves_promotion_hashes": "replay_required",
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
