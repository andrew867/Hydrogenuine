"""Operator review schemas."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash

WORKSPACE = Path(__file__).resolve().parents[2]
OPERATOR_REVIEW_POLICY_PATH = WORKSPACE / "configs/agent_zero/operator_review_policy.json"
EXCITON_REVIEW_VISIBILITY_POLICY_PATH = WORKSPACE / "configs/agent_zero/exciton_review_visibility_policy.json"

FRESHNESS_TTL_SECONDS = 300
STALE_TTL_SECONDS = 900


class ReviewAction(str, Enum):
    HOLD = "hold"
    REJECT = "reject"
    NEEDS_EDIT = "needs_edit"
    ARCHIVE = "archive"
    ADD_OPERATOR_NOTE = "add_operator_note"
    # Forbidden in Phase 10 — listed for validation only
    APPROVE = "approve"
    APPROVE_FOR_PUBLISH = "approve_for_publish"
    PUBLISH = "publish"
    SEND = "send"
    REPLY_LIVE = "reply_live"
    COMMENT_LIVE = "comment_live"
    BROWSER_SUBMIT = "browser_submit"
    EXTERNAL_EXECUTE = "external_execute"
    HARDWARE_ACTUATE = "hardware_actuate"


FORBIDDEN_REVIEW_ACTIONS = frozenset({
    ReviewAction.APPROVE,
    ReviewAction.APPROVE_FOR_PUBLISH,
    ReviewAction.PUBLISH,
    ReviewAction.SEND,
    ReviewAction.REPLY_LIVE,
    ReviewAction.COMMENT_LIVE,
    ReviewAction.BROWSER_SUBMIT,
    ReviewAction.EXTERNAL_EXECUTE,
    ReviewAction.HARDWARE_ACTUATE,
})

ALLOWED_REVIEW_ACTIONS = frozenset({
    ReviewAction.HOLD,
    ReviewAction.REJECT,
    ReviewAction.NEEDS_EDIT,
    ReviewAction.ARCHIVE,
    ReviewAction.ADD_OPERATOR_NOTE,
})


class ReviewItemStatus(str, Enum):
    QUEUED = "queued"
    HELD = "held"
    NEEDS_EDIT = "needs_edit"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class ReviewQueueVerdict(str, Enum):
    GREEN_REVIEW_QUEUE_READY = "GREEN_REVIEW_QUEUE_READY"
    YELLOW_REVIEW_QUEUE_EMPTY_FRESH = "YELLOW_REVIEW_QUEUE_EMPTY_FRESH"
    YELLOW_REVIEW_QUEUE_STALE = "YELLOW_REVIEW_QUEUE_STALE"
    RED_REVIEW_QUEUE_EMPTY_GREEN_WITHOUT_SOURCE = "RED_REVIEW_QUEUE_EMPTY_GREEN_WITHOUT_SOURCE"
    RED_REVIEW_QUEUE_STALE_GREEN = "RED_REVIEW_QUEUE_STALE_GREEN"
    RED_REVIEW_ITEM_SOURCELESS = "RED_REVIEW_ITEM_SOURCELESS"


class ReviewDecisionVerdict(str, Enum):
    GREEN_REVIEW_DECISION_RECORDED = "GREEN_REVIEW_DECISION_RECORDED"
    RED_REVIEW_DECISION_RECEIPT_MISSING = "RED_REVIEW_DECISION_RECEIPT_MISSING"
    RED_REVIEW_DECISION_EXTERNAL_SIDE_EFFECT = "RED_REVIEW_DECISION_EXTERNAL_SIDE_EFFECT"
    RED_REVIEW_ACTION_FORBIDDEN = "RED_REVIEW_ACTION_FORBIDDEN"


class ReviewItemTruthVerdict(str, Enum):
    GREEN_REVIEW_ITEM_LIVE_LOCAL_READY = "GREEN_REVIEW_ITEM_LIVE_LOCAL_READY"
    YELLOW_REVIEW_ITEM_STALE = "YELLOW_REVIEW_ITEM_STALE"
    YELLOW_REVIEW_ITEM_FIXTURE_LABELLED = "YELLOW_REVIEW_ITEM_FIXTURE_LABELLED"
    RED_REVIEW_ITEM_FIXTURE_UNLABELLED = "RED_REVIEW_ITEM_FIXTURE_UNLABELLED"
    RED_REVIEW_ITEM_SOURCE_MISSING = "RED_REVIEW_ITEM_SOURCE_MISSING"
    RED_REVIEW_ITEM_QUALITY_MISSING = "RED_REVIEW_ITEM_QUALITY_MISSING"
    RED_REVIEW_ITEM_HASH_MISSING = "RED_REVIEW_ITEM_HASH_MISSING"


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_from_now(ttl_seconds: int = FRESHNESS_TTL_SECONDS) -> str:
    from datetime import timedelta

    return (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()


def load_operator_review_policy() -> dict[str, Any]:
    if OPERATOR_REVIEW_POLICY_PATH.is_file():
        return json.loads(OPERATOR_REVIEW_POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def load_exciton_review_visibility_policy() -> dict[str, Any]:
    if EXCITON_REVIEW_VISIBILITY_POLICY_PATH.is_file():
        return json.loads(EXCITON_REVIEW_VISIBILITY_POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def new_review_item_id() -> str:
    return f"review-item-{uuid.uuid4().hex[:12]}"


def new_snapshot_id() -> str:
    return f"review-snap-{uuid.uuid4().hex[:12]}"


def new_decision_id() -> str:
    return f"review-dec-{uuid.uuid4().hex[:12]}"


def new_decision_receipt_id() -> str:
    return f"review-receipt-{uuid.uuid4().hex[:12]}"


def new_truth_state_id() -> str:
    return f"truth-{uuid.uuid4().hex[:12]}"


@dataclass
class OperatorReviewItem:
    review_item_id: str
    candidate_ref: str
    artifact_ref: str
    artifact_hash: str
    quality_receipt_ref: str
    source_refs: list[str]
    provider_receipt_refs: list[str]
    status: ReviewItemStatus
    created_at: str
    updated_at: str
    truth_state_ref: str
    hash: str = ""
    turn_receipt_ref: str | None = None
    broker_decision_ref: str | None = None
    surface: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "review_item_id": self.review_item_id,
            "candidate_ref": self.candidate_ref,
            "artifact_ref": self.artifact_ref,
            "artifact_hash": self.artifact_hash,
            "quality_receipt_ref": self.quality_receipt_ref,
            "source_refs": list(self.source_refs),
            "provider_receipt_refs": list(self.provider_receipt_refs),
            "turn_receipt_ref": self.turn_receipt_ref,
            "broker_decision_ref": self.broker_decision_ref,
            "surface": self.surface,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "truth_state_ref": self.truth_state_ref,
            "hash": self.hash,
        }

    def with_hash(self) -> OperatorReviewItem:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return OperatorReviewItem(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class OperatorReviewQueueSnapshot:
    snapshot_id: str
    item_count: int
    items: list[OperatorReviewItem]
    source_store_ref: str
    freshness_status: FreshnessStatus
    generated_at: str
    expires_at: str
    verdict: ReviewQueueVerdict
    hash: str = ""
    run_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "run_id": self.run_id,
            "item_count": self.item_count,
            "items": [i.to_payload() for i in self.items],
            "source_store_ref": self.source_store_ref,
            "freshness_status": self.freshness_status.value,
            "generated_at": self.generated_at,
            "expires_at": self.expires_at,
            "verdict": self.verdict.value,
            "hash": self.hash,
        }

    def with_hash(self) -> OperatorReviewQueueSnapshot:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return OperatorReviewQueueSnapshot(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class OperatorReviewDecision:
    decision_id: str
    review_item_ref: str
    action: ReviewAction
    reason: str
    created_at: str
    hash: str = ""
    operator_ref: str | None = None
    operator_note: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "review_item_ref": self.review_item_ref,
            "action": self.action.value,
            "operator_ref": self.operator_ref,
            "operator_note": self.operator_note,
            "reason": self.reason,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> OperatorReviewDecision:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return OperatorReviewDecision(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class OperatorReviewDecisionReceipt:
    decision_receipt_id: str
    decision_ref: str
    review_item_ref: str
    artifact_hash_before: str
    quality_receipt_ref: str
    external_side_effect: bool
    published: bool
    sent: bool
    status_before: str
    status_after: str
    created_at: str
    hash: str = ""
    artifact_hash_after: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_receipt_id": self.decision_receipt_id,
            "decision_ref": self.decision_ref,
            "review_item_ref": self.review_item_ref,
            "artifact_hash_before": self.artifact_hash_before,
            "artifact_hash_after": self.artifact_hash_after,
            "quality_receipt_ref": self.quality_receipt_ref,
            "external_side_effect": self.external_side_effect,
            "published": self.published,
            "sent": self.sent,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> OperatorReviewDecisionReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return OperatorReviewDecisionReceipt(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class ReviewItemTruthState:
    truth_state_id: str
    review_item_ref: str
    artifact_ref: str
    artifact_hash: str
    quality_receipt_ref: str
    source_refs: list[str]
    provider_receipt_refs: list[str]
    freshness_status: FreshnessStatus
    data_tier: str
    verdict: ReviewItemTruthVerdict
    generated_at: str
    expires_at: str
    hash: str = ""
    fixture_label: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "truth_state_id": self.truth_state_id,
            "review_item_ref": self.review_item_ref,
            "artifact_ref": self.artifact_ref,
            "artifact_hash": self.artifact_hash,
            "quality_receipt_ref": self.quality_receipt_ref,
            "source_refs": list(self.source_refs),
            "provider_receipt_refs": list(self.provider_receipt_refs),
            "freshness_status": self.freshness_status.value,
            "data_tier": self.data_tier,
            "fixture_label": self.fixture_label,
            "verdict": self.verdict.value,
            "generated_at": self.generated_at,
            "expires_at": self.expires_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ReviewItemTruthState:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ReviewItemTruthState(**{**self.__dict__, "hash": hash_record(body)})


def verify_review_hash(payload: dict[str, Any]) -> bool:
    h = payload.get("hash", "")
    if not h:
        return False
    body = {k: v for k, v in payload.items() if k != "hash"}
    return verify_record_hash(body, h)


__all__ = [
    "ALLOWED_REVIEW_ACTIONS",
    "FORBIDDEN_REVIEW_ACTIONS",
    "FRESHNESS_TTL_SECONDS",
    "FreshnessStatus",
    "OperatorReviewDecision",
    "OperatorReviewDecisionReceipt",
    "OperatorReviewItem",
    "OperatorReviewQueueSnapshot",
    "ReviewAction",
    "ReviewDecisionVerdict",
    "ReviewItemStatus",
    "ReviewItemTruthState",
    "ReviewItemTruthVerdict",
    "ReviewQueueVerdict",
    "STALE_TTL_SECONDS",
    "load_exciton_review_visibility_policy",
    "load_operator_review_policy",
    "new_decision_id",
    "new_decision_receipt_id",
    "new_review_item_id",
    "new_snapshot_id",
    "new_truth_state_id",
    "now_iso",
    "verify_review_hash",
]
