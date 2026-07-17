"""Operator review decisions — local only, receipt required."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.operator_review.errors import ForbiddenReviewActionError, ReviewDecisionError, ReviewStoreError
from hg_runtime.operator_review.redaction import validate_operator_note
from hg_runtime.operator_review.review_queue import build_review_queue_snapshot
from hg_runtime.operator_review.review_store import ReviewStore
from hg_runtime.operator_review.schema import (
    ALLOWED_REVIEW_ACTIONS,
    FORBIDDEN_REVIEW_ACTIONS,
    OperatorReviewDecision,
    OperatorReviewDecisionReceipt,
    OperatorReviewItem,
    ReviewAction,
    ReviewDecisionVerdict,
    ReviewItemStatus,
    load_operator_review_policy,
    new_decision_id,
    new_decision_receipt_id,
    now_iso,
)
from hg_runtime.output_artifacts.artifact_store import ArtifactStore


@dataclass
class DecisionResult:
    verdict: ReviewDecisionVerdict
    decision: OperatorReviewDecision | None = None
    receipt: OperatorReviewDecisionReceipt | None = None
    receipt_path: str | None = None


def _ensure_allowed(action: ReviewAction) -> None:
    policy = load_operator_review_policy()
    forbidden = {ReviewAction(a) for a in policy.get("forbidden_review_actions", [])}
    if action in FORBIDDEN_REVIEW_ACTIONS or action in forbidden:
        raise ForbiddenReviewActionError(action.value)
    if action not in ALLOWED_REVIEW_ACTIONS:
        raise ForbiddenReviewActionError(action.value)


def _status_for_action(action: ReviewAction) -> ReviewItemStatus:
    return {
        ReviewAction.HOLD: ReviewItemStatus.HELD,
        ReviewAction.REJECT: ReviewItemStatus.REJECTED,
        ReviewAction.NEEDS_EDIT: ReviewItemStatus.NEEDS_EDIT,
        ReviewAction.ARCHIVE: ReviewItemStatus.ARCHIVED,
        ReviewAction.ADD_OPERATOR_NOTE: ReviewItemStatus.QUEUED,
    }[action]


def _resolve_review_item(
    store: ReviewStore,
    *,
    review_item_id: str | None = None,
    candidate_ref: str | None = None,
) -> dict[str, Any]:
    if review_item_id:
        return store.read_review_item(review_item_id)
    if candidate_ref:
        found = store.find_item_by_candidate(candidate_ref)
        if found:
            return found
        snap = build_review_queue_snapshot(store.run_id, review_base=store.base)
        found = store.find_item_by_candidate(candidate_ref)
        if found:
            return found
        for item in snap.items:
            if item.candidate_ref == candidate_ref:
                return store.read_review_item(item.review_item_id)
    raise ReviewStoreError("review item not found")


def record_review_decision(
    *,
    run_id: str,
    action: ReviewAction,
    reason: str,
    review_item_id: str | None = None,
    candidate_ref: str | None = None,
    operator_ref: str | None = None,
    operator_note: str | None = None,
    review_base: Path | None = None,
    artifact_base: Path | None = None,
) -> DecisionResult:
    _ensure_allowed(action)
    if action == ReviewAction.ADD_OPERATOR_NOTE:
        ok, err = validate_operator_note(operator_note or "")
        if not ok:
            raise ReviewDecisionError(err or "invalid_note")

    review_store = ReviewStore(run_id, base=review_base)
    item_payload = _resolve_review_item(
        review_store, review_item_id=review_item_id, candidate_ref=candidate_ref
    )
    status_before = item_payload.get("status", ReviewItemStatus.QUEUED.value)
    if action == ReviewAction.ADD_OPERATOR_NOTE:
        status_after = status_before
    else:
        status_after = _status_for_action(action).value

    artifact_hash_before = item_payload.get("artifact_hash", "")
    artifact_hash_after: str | None = artifact_hash_before
    if action == ReviewAction.NEEDS_EDIT:
        artifact_hash_after = None

    decision = OperatorReviewDecision(
        decision_id=new_decision_id(),
        review_item_ref=item_payload["review_item_id"],
        action=action,
        operator_ref=operator_ref,
        operator_note=operator_note,
        reason=reason,
        created_at=now_iso(),
    ).with_hash()
    review_store.store_decision(decision)

    receipt = OperatorReviewDecisionReceipt(
        decision_receipt_id=new_decision_receipt_id(),
        decision_ref=decision.decision_id,
        review_item_ref=item_payload["review_item_id"],
        artifact_hash_before=artifact_hash_before,
        artifact_hash_after=artifact_hash_after,
        quality_receipt_ref=item_payload.get("quality_receipt_ref", ""),
        external_side_effect=False,
        published=False,
        sent=False,
        status_before=status_before,
        status_after=status_after,
        created_at=now_iso(),
    ).with_hash()
    receipt_path = review_store.store_decision_receipt(receipt)

    updated = OperatorReviewItem(
        review_item_id=item_payload["review_item_id"],
        candidate_ref=item_payload["candidate_ref"],
        artifact_ref=item_payload["artifact_ref"],
        artifact_hash=artifact_hash_before if artifact_hash_after else "",
        quality_receipt_ref=item_payload["quality_receipt_ref"],
        source_refs=list(item_payload.get("source_refs") or []),
        provider_receipt_refs=list(item_payload.get("provider_receipt_refs") or []),
        turn_receipt_ref=item_payload.get("turn_receipt_ref"),
        broker_decision_ref=item_payload.get("broker_decision_ref"),
        surface=item_payload.get("surface"),
        status=ReviewItemStatus(status_after),
        created_at=item_payload.get("created_at", now_iso()),
        updated_at=now_iso(),
        truth_state_ref=item_payload.get("truth_state_ref", ""),
    ).with_hash()
    review_store.update_review_item(updated)

    return DecisionResult(
        verdict=ReviewDecisionVerdict.GREEN_REVIEW_DECISION_RECORDED,
        decision=decision,
        receipt=receipt,
        receipt_path=str(receipt_path),
    )


def attempt_forbidden_action(action: str, *, run_id: str, candidate_ref: str, review_base: Path | None = None) -> DecisionResult:
    try:
        act = ReviewAction(action)
    except ValueError:
        act = ReviewAction.APPROVE
    try:
        _ensure_allowed(act)
    except ForbiddenReviewActionError:
        return DecisionResult(verdict=ReviewDecisionVerdict.RED_REVIEW_ACTION_FORBIDDEN)
    raise ReviewDecisionError("action not forbidden")


def hold_review_item(**kwargs: Any) -> DecisionResult:
    return record_review_decision(action=ReviewAction.HOLD, reason=kwargs.pop("reason", "operator_hold"), **kwargs)


def reject_review_item(**kwargs: Any) -> DecisionResult:
    return record_review_decision(action=ReviewAction.REJECT, reason=kwargs.pop("reason", "operator_reject"), **kwargs)


def mark_review_item_needs_edit(**kwargs: Any) -> DecisionResult:
    return record_review_decision(action=ReviewAction.NEEDS_EDIT, reason=kwargs.pop("reason", "needs_edit"), **kwargs)


def archive_review_item(**kwargs: Any) -> DecisionResult:
    return record_review_decision(action=ReviewAction.ARCHIVE, reason=kwargs.pop("reason", "archived"), **kwargs)


def add_operator_note(**kwargs: Any) -> DecisionResult:
    note = kwargs.pop("operator_note", kwargs.pop("note", ""))
    return record_review_decision(
        action=ReviewAction.ADD_OPERATOR_NOTE,
        reason=kwargs.pop("reason", "operator_note"),
        operator_note=note,
        **kwargs,
    )


__all__ = [
    "DecisionResult",
    "add_operator_note",
    "archive_review_item",
    "attempt_forbidden_action",
    "hold_review_item",
    "mark_review_item_needs_edit",
    "record_review_decision",
    "reject_review_item",
]
