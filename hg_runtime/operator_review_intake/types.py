"""ORI types — operator review receipts; approval evidence requires IAM binding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.ori_cluster.errors import OriValidationError
from hg_core.policy_safety.hashing import compute_record_hash

ORI_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-14T12:00:00.000000Z"

OperatorAction = Literal[
    "approved",
    "approved_with_scope",
    "accepted",
    "signed",
    "authorized",
    "rejected",
    "deferred",
    "requested_more_info",
    "needs_more_info",
    "dismissed",
    "expired",
    "no_action",
    "queued",
    "viewed",
    "operator_unavailable",
    "unknown",
]

APPROVAL_EVIDENCE_ACTIONS = frozenset(
    {
        "approved",
        "approved_with_scope",
        "accepted",
        "signed",
        "authorized",
    }
)

NON_APPROVAL_OPTIONAL_OPERATOR_REF = frozenset(
    {
        "rejected",
        "deferred",
        "requested_more_info",
        "needs_more_info",
        "dismissed",
        "expired",
        "no_action",
        "queued",
        "viewed",
        "operator_unavailable",
        "unknown",
    }
)

_BARE_PLACEHOLDER_REFS = frozenset(
    {
        "",
        "operator",
        "operator_id",
        "human",
        "user",
        "admin",
        "TBD",
        "unknown",
        "placeholder",
    }
)


def is_approval_evidence_action(action: str) -> bool:
    return action in APPROVAL_EVIDENCE_ACTIONS


def is_bare_operator_ref(operator_ref: str | None) -> bool:
    raw = str(operator_ref or "").strip()
    if not raw:
        return True
    if raw in _BARE_PLACEHOLDER_REFS:
        return True
    if ":" not in raw and not raw.startswith("op:"):
        return True
    return False


@dataclass(frozen=True)
class OperatorReviewReceipt:
    receipt_id: str
    review_item_ref: str
    operator_action: OperatorAction
    operator_ref: str | None = None
    approval_scope: str | None = None
    scope_ref: str | None = None
    approval_expires_at: str | None = None
    resulting_route_ref: str | None = None
    record_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_no_secrets(
            self.receipt_id,
            self.review_item_ref,
            str(self.operator_ref or ""),
            str(self.approval_scope or ""),
            str(self.scope_ref or ""),
            str(self.resulting_route_ref or ""),
        )
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def resolved_scope(self) -> str | None:
        scope = (self.approval_scope or self.scope_ref or "").strip()
        return scope or None

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "ori-operator-review-receipt",
            "schema_version": ORI_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "review_item_ref": self.review_item_ref,
            "operator_action": self.operator_action,
            "authority_created": False,
        }
        if self.operator_ref:
            payload["operator_ref"] = self.operator_ref
        scope = self.resolved_scope()
        if scope:
            payload["approval_scope"] = scope
        if self.approval_expires_at:
            payload["approval_expires_at"] = self.approval_expires_at
        if self.resulting_route_ref:
            payload["resulting_route_ref"] = self.resulting_route_ref
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=secret" in lower:
            raise OriValidationError("ori.validation.secret", "secrets forbidden in ORI records")


def receipt_from_fixture(fixture: dict[str, str]) -> OperatorReviewReceipt:
    return OperatorReviewReceipt(
        receipt_id=fixture["receipt_id"],
        review_item_ref=fixture.get("review_item_ref", "ori-item:fixture"),
        operator_action=fixture.get("operator_action", "deferred"),  # type: ignore[arg-type]
        operator_ref=fixture.get("operator_ref") or None,
        approval_scope=fixture.get("approval_scope") or fixture.get("scope_ref") or None,
        scope_ref=fixture.get("scope_ref") or fixture.get("approval_scope") or None,
        approval_expires_at=fixture.get("approval_expires_at") or None,
        resulting_route_ref=fixture.get("resulting_route_ref") or None,
    )


__all__ = [
    "APPROVAL_EVIDENCE_ACTIONS",
    "FIXTURE_CLOCK",
    "NON_APPROVAL_OPTIONAL_OPERATOR_REF",
    "ORI_SCHEMA_VERSION",
    "OperatorAction",
    "OperatorReviewReceipt",
    "is_approval_evidence_action",
    "is_bare_operator_ref",
    "receipt_from_fixture",
]
