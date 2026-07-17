"""Social review queue schema — per-item operator approval before publish."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.social_capability.schema import _frozen, new_id, social_hash


class SocialReviewStatus(str, Enum):
    QUEUED = "queued"
    APPROVED = "approved"
    DENIED = "denied"
    PUBLISHED = "published"
    PUBLISHED_LEGACY_UNCONFIRMED = "published_legacy_unconfirmed"
    EXPIRED = "expired"
    INVALID = "invalid"


class SocialReviewDecision(str, Enum):
    APPROVE = "approve"
    DENY = "deny"


class SocialDeniedReason(str, Enum):
    OPERATOR_DENIED = "operator_denied"
    NOT_SUITABLE = "not_suitable"
    TRUST_BOUNDARY = "trust_boundary"
    RATE_LIMIT = "rate_limit"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class SocialApprovalToken:
    """Single-use scoped approval for one queue item — not global permission."""

    token_id: str
    queue_item_id: str
    draft_id: str
    issued_at: str
    consumed: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "queue_item_id": self.queue_item_id,
            "draft_id": self.draft_id,
            "issued_at": self.issued_at,
            "consumed": self.consumed,
            **_frozen(),
        }


@dataclass
class SocialReviewItem:
    queue_item_id: str
    draft_id: str
    draft_hash: str
    surface_id: str
    created_at: str
    source_task_ref: str
    sanitized_preview: str
    full_text_path: str | None = None
    trust_boundary_verdict: str = "UNKNOWN"
    opb_verdict: str = "UNKNOWN"
    permit_template_ref: str | None = None
    rate_limit_status: str = "OK"
    publish_eligible: bool = False
    status: SocialReviewStatus = SocialReviewStatus.QUEUED
    approval_receipt_ref: str | None = None
    denial_receipt_ref: str | None = None
    publish_receipt_ref: str | None = None
    operator_ref: str | None = None
    approval_handle: str | None = None
    incident_class: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "queue_item_id": self.queue_item_id,
            "draft_id": self.draft_id,
            "draft_hash": self.draft_hash,
            "surface_id": self.surface_id,
            "created_at": self.created_at,
            "source_task_ref": self.source_task_ref,
            "sanitized_preview": self.sanitized_preview[:500],
            "full_text_path": self.full_text_path,
            "trust_boundary_verdict": self.trust_boundary_verdict,
            "opb_verdict": self.opb_verdict,
            "permit_template_ref": self.permit_template_ref,
            "rate_limit_status": self.rate_limit_status,
            "publish_eligible": self.publish_eligible,
            "status": self.status.value,
            "approval_receipt_ref": self.approval_receipt_ref,
            "denial_receipt_ref": self.denial_receipt_ref,
            "publish_receipt_ref": self.publish_receipt_ref,
            "operator_ref": self.operator_ref,
            "approval_handle": self.approval_handle,
            "incident_class": self.incident_class,
            **_frozen(),
        }
        payload["item_hash"] = social_hash(
            {k: v for k, v in payload.items() if k not in ("item_hash",)}
        )
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "SocialReviewItem":
        return cls(
            queue_item_id=data["queue_item_id"],
            draft_id=data["draft_id"],
            draft_hash=data.get("draft_hash", ""),
            surface_id=data.get("surface_id", "unknown"),
            created_at=data.get("created_at", ""),
            source_task_ref=data.get("source_task_ref", ""),
            sanitized_preview=data.get("sanitized_preview", ""),
            full_text_path=data.get("full_text_path"),
            trust_boundary_verdict=data.get("trust_boundary_verdict", "UNKNOWN"),
            opb_verdict=data.get("opb_verdict", "UNKNOWN"),
            permit_template_ref=data.get("permit_template_ref"),
            rate_limit_status=data.get("rate_limit_status", "OK"),
            publish_eligible=bool(data.get("publish_eligible", False)),
            status=SocialReviewStatus(data.get("status", "queued")),
            approval_receipt_ref=data.get("approval_receipt_ref"),
            denial_receipt_ref=data.get("denial_receipt_ref"),
            publish_receipt_ref=data.get("publish_receipt_ref"),
            operator_ref=data.get("operator_ref"),
            approval_handle=data.get("approval_handle"),
            incident_class=data.get("incident_class"),
        )


@dataclass
class SocialReviewQueue:
    run_dir: str
    items: list[SocialReviewItem] = field(default_factory=list)
    legacy_incident_recorded: bool = False
    live_publish_paused: bool = False
    approved_only_mode: bool = False
    auto_approve_queued_items: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "social-review-queue",
            "run_dir": self.run_dir,
            "items": [i.to_payload() for i in self.items],
            "legacy_incident_recorded": self.legacy_incident_recorded,
            "live_publish_paused": self.live_publish_paused,
            "approved_only_mode": self.approved_only_mode,
            "auto_approve_queued_items": self.auto_approve_queued_items,
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "SocialReviewQueue":
        return cls(
            run_dir=data.get("run_dir", ""),
            items=[SocialReviewItem.from_payload(i) for i in data.get("items", [])],
            legacy_incident_recorded=bool(data.get("legacy_incident_recorded", False)),
            live_publish_paused=bool(data.get("live_publish_paused", False)),
            approved_only_mode=bool(data.get("approved_only_mode", False)),
            auto_approve_queued_items=bool(data.get("auto_approve_queued_items", False)),
        )


@dataclass
class SocialReviewReceipt:
    receipt_id: str
    decision: SocialReviewDecision
    queue_item_id: str
    draft_id: str
    created_at: str
    operator_ref: str
    reason: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "social-review-receipt",
            "receipt_id": self.receipt_id,
            "decision": self.decision.value,
            "queue_item_id": self.queue_item_id,
            "draft_id": self.draft_id,
            "created_at": self.created_at,
            "operator_ref": self.operator_ref,
            "reason": self.reason[:500],
            **_frozen(),
        }


def new_queue_item_id() -> str:
    return new_id("sri")


def new_review_receipt_id() -> str:
    return new_id("srr")


__all__ = [
    "SocialApprovalToken",
    "SocialDeniedReason",
    "SocialReviewDecision",
    "SocialReviewItem",
    "SocialReviewQueue",
    "SocialReviewReceipt",
    "SocialReviewStatus",
    "new_queue_item_id",
    "new_review_receipt_id",
]
