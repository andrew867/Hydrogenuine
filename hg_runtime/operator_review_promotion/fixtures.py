"""Deterministic ORP-0 fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.evidence_review_queue import build_fixture_targets, build_review_queue
from hg_runtime.operator_review_promotion.decision import (
    build_operator_deferral_record,
    build_operator_rejection_record,
    build_operator_review_decision,
    build_reviewed_evidence_link,
)
from hg_runtime.operator_review_promotion.decision_policy import build_promotion_policy_receipt
from hg_runtime.operator_review_promotion.promotion_gate import build_promotion_gate_result
from hg_runtime.operator_review_promotion.promotion_request import build_evidence_promotion_request
from hg_runtime.operator_review_promotion.schemas import DECISION_STATUSES, assert_neutral, record_hash


def build_orp0_layer(root: Path) -> dict:
    targets = build_fixture_targets(root)
    queue = build_review_queue(targets=targets, fever_level="NORMAL")
    tasks = queue["tasks"]
    decisions = [
        build_operator_review_decision(
            decision_id=f"operator-review-decision-{index:03d}",
            review_task=tasks[(index - 1) % len(tasks)],
            status=status,
            rationale=f"fixture_{status.lower()}",
        )
        for index, status in enumerate(DECISION_STATUSES, start=1)
    ]
    approved = next(d for d in decisions if d["decision_status"] == "APPROVE_FOR_PROVISIONAL_USE")
    rejected = next(d for d in decisions if d["decision_status"] == "REJECT_SOURCE")
    deferred = next(d for d in decisions if d["decision_status"] == "DEFER_REVIEW")
    request = build_evidence_promotion_request(request_id="promotion-request-001", decision=approved)
    gate_result = build_promotion_gate_result(gate_result_id="promotion-gate-result-001", request=request, passed=False)
    links = [build_reviewed_evidence_link(link_id=f"reviewed-evidence-link-{i:03d}", decision=d) for i, d in enumerate(decisions, start=1)]
    rejections = [build_operator_rejection_record(rejection_id="operator-rejection-001", decision=rejected)]
    deferrals = [build_operator_deferral_record(deferral_id="operator-deferral-001", decision=deferred)]
    policy = build_promotion_policy_receipt()
    replay = replay_orp0(decisions, links, [request], [gate_result], policy)
    manifest = {
        "schema_version": "1",
        "record_type": "operator_review_manifest_v1",
        "manifest_id": "orp0-operator-review-manifest",
        "decision_count": len(decisions),
        "decision_statuses": [d["decision_status"] for d in decisions],
        "reviewed_evidence_link_count": len(links),
        "promotion_request_count": 1,
        "promotion_gate_result_count": 1,
        "rejection_record_count": len(rejections),
        "deferral_record_count": len(deferrals),
        "operator_review_is_truth": False,
        "promotion_request_is_promotion": False,
        "promotion_gate_is_truth": False,
        "belief_promotion_automatic": False,
        "live_effects_created": False,
        "decision_hashes": [d["decision_hash"] for d in decisions],
        "link_hashes": [l["record_hash"] for l in links],
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return {
        "source_review_queue": queue,
        "policy": policy,
        "decisions": decisions,
        "manifest": manifest,
        "promotion_requests": [request],
        "promotion_gate_results": [gate_result],
        "reviewed_evidence_links": links,
        "operator_rejection_records": rejections,
        "operator_deferral_records": deferrals,
        "replay": replay,
    }


def replay_orp0(
    decisions: list[dict],
    links: list[dict],
    promotion_requests: list[dict],
    promotion_gate_results: list[dict],
    policy: dict,
) -> dict:
    chain = (
        [policy]
        + sorted(decisions, key=lambda item: item["decision_id"])
        + sorted(links, key=lambda item: item["link_id"])
        + sorted(promotion_requests, key=lambda item: item["promotion_request_id"])
        + sorted(promotion_gate_results, key=lambda item: item["promotion_gate_result_id"])
    )
    root = record_hash({"records": [record_hash(item) for item in chain]})
    replay = {
        "schema_version": "1",
        "record_type": "operator_review_replay_record_v1",
        "replay_id": "orp0-operator-review-replay",
        "record_count": len(chain),
        "receipt_chain_root": root,
        "replay_preserves_review_hashes": True,
        "replay_preserves_policy_hash": bool(policy.get("record_hash")),
        "operator_review_treated_as_truth": False,
        "belief_promotion_automatic": False,
    }
    replay["record_hash"] = record_hash(replay)
    return replay
