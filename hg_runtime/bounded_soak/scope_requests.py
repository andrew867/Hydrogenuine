"""Scope request records — advisory, never grants permission."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash


class ScopeRequestKind(str, Enum):
    MORE_TIME = "more_time"
    MORE_READ_SCOPE = "more_read_scope"
    NEW_SURFACE = "new_surface"
    OPERATOR_CONTEXT = "operator_context"
    LIVE_PROVIDER = "live_provider"
    LIVE_SOCIAL_CREDENTIALS = "live_social_credentials"
    EXTERNAL_ACTION_PERMISSION = "external_action_permission"
    HARDWARE_SCOPE = "hardware_scope"
    UNKNOWN = "unknown"


class ScopeRequestVerdict(str, Enum):
    GREEN_SCOPE_REQUEST_VALID = "GREEN_SCOPE_REQUEST_VALID"
    RED_SCOPE_REQUEST_EMPTY = "RED_SCOPE_REQUEST_EMPTY"
    RED_SCOPE_REQUEST_GRANTS_PERMISSION = "RED_SCOPE_REQUEST_GRANTS_PERMISSION"


@dataclass(frozen=True)
class ScopeRequest:
    request_id: str
    kind: ScopeRequestKind
    rationale: str
    permission_granted: bool = False
    queued_for_operator: bool = True
    created_at: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "kind": self.kind.value,
            "rationale": self.rationale,
            "permission_granted": self.permission_granted,
            "queued_for_operator": self.queued_for_operator,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ScopeRequestReceipt:
    request_id: str
    kind: ScopeRequestKind
    rationale: str
    advisory_only: bool = True
    permission_granted: bool = False
    hash: str = ""
    created_at: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "kind": self.kind.value,
            "rationale": self.rationale,
            "advisory_only": self.advisory_only,
            "permission_granted": self.permission_granted,
            "hash": self.hash,
            "created_at": self.created_at,
        }


def create_scope_request(
    *,
    kind: ScopeRequestKind,
    rationale: str,
    from_unbounded_desire: bool = False,
) -> ScopeRequestReceipt:
    """Create advisory scope request — unbounded desire becomes request, not action."""
    if not rationale or not rationale.strip():
        raise ValueError("RED_SCOPE_REQUEST_EMPTY")
    rid = f"scope-req-{uuid.uuid4().hex[:16]}"
    ts = datetime.now(timezone.utc).isoformat()
    body = {
        "request_id": rid,
        "kind": kind.value,
        "rationale": rationale.strip(),
        "advisory_only": True,
        "permission_granted": False,
        "created_at": ts,
    }
    digest = compute_record_hash(body)
    return ScopeRequestReceipt(
        request_id=rid,
        kind=kind,
        rationale=rationale.strip(),
        advisory_only=True,
        permission_granted=False,
        hash=digest,
        created_at=ts,
    )


def validate_scope_request(receipt: ScopeRequestReceipt) -> ScopeRequestVerdict:
    """Validate scope request invariants."""
    if not receipt.rationale or not receipt.rationale.strip():
        return ScopeRequestVerdict.RED_SCOPE_REQUEST_EMPTY
    if receipt.permission_granted:
        return ScopeRequestVerdict.RED_SCOPE_REQUEST_GRANTS_PERMISSION
    expected = compute_record_hash({
        "request_id": receipt.request_id,
        "kind": receipt.kind.value,
        "rationale": receipt.rationale,
        "advisory_only": receipt.advisory_only,
        "permission_granted": receipt.permission_granted,
        "created_at": receipt.created_at,
    })
    if receipt.hash and receipt.hash != expected:
        return ScopeRequestVerdict.RED_SCOPE_REQUEST_EMPTY
    return ScopeRequestVerdict.GREEN_SCOPE_REQUEST_VALID


def unbounded_desire_to_scope_request(desire: str) -> ScopeRequestReceipt:
    """Convert unbounded desire into scope request — never into action."""
    return create_scope_request(
        kind=ScopeRequestKind.UNKNOWN,
        rationale=desire,
        from_unbounded_desire=True,
    )


__all__ = [
    "ScopeRequest",
    "ScopeRequestKind",
    "ScopeRequestReceipt",
    "ScopeRequestVerdict",
    "create_scope_request",
    "unbounded_desire_to_scope_request",
    "validate_scope_request",
]
