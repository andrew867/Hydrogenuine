"""Capability lease lifecycle (hg.lease.v1) — explicit state machine.

Transitions are table-driven, reason-coded, idempotent per event_id, and fail
closed on anything not in the table. Terminal states accept no transitions.
No API here can broaden scope, extend duration, or raise limits — a changed
policy always means a new lease that supersedes the old one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash

LEASE_SCHEMA_VERSION = "hg.lease.v1"

STATES = (
    "DRAFT",
    "PENDING",
    "ACTIVE",
    "SUSPENDED",
    "EXPIRED",
    "EXHAUSTED",
    "REVOKED",
    "SUPERSEDED",
    "FAILED",
)
TERMINAL_STATES = frozenset({"EXPIRED", "EXHAUSTED", "REVOKED", "SUPERSEDED", "FAILED"})

# (state, event) -> next state. Anything absent is an invalid transition.
TRANSITIONS: dict[tuple[str, str], str] = {
    ("DRAFT", "submit"): "PENDING",
    ("PENDING", "confirm"): "ACTIVE",
    ("PENDING", "reject"): "FAILED",
    ("PENDING", "expire"): "EXPIRED",
    ("ACTIVE", "suspend"): "SUSPENDED",
    ("ACTIVE", "expire"): "EXPIRED",
    ("ACTIVE", "exhaust"): "EXHAUSTED",
    ("ACTIVE", "revoke"): "REVOKED",
    ("ACTIVE", "supersede"): "SUPERSEDED",
    ("ACTIVE", "fail"): "FAILED",
    ("SUSPENDED", "resume"): "ACTIVE",
    ("SUSPENDED", "expire"): "EXPIRED",
    ("SUSPENDED", "revoke"): "REVOKED",
    ("SUSPENDED", "supersede"): "SUPERSEDED",
    ("SUSPENDED", "fail"): "FAILED",
}


class LeaseTransitionError(RuntimeError):
    """Invalid lifecycle transition — fail closed."""


@dataclass(frozen=True)
class LifecycleEvent:
    event_id: str
    lease_id: str
    event: str
    from_state: str
    to_state: str
    reason_code: str
    at_wall: str
    detail: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "hg.lease.event.v1",
            "event_id": self.event_id,
            "lease_id": self.lease_id,
            "event": self.event,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason_code": self.reason_code,
            "at_wall": self.at_wall,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CapabilityLease:
    lease_id: str
    policy_id: str
    policy_hash: str
    issuer: str
    subject: str
    action_scope: tuple[str, ...]
    object_scope: tuple[str, ...]
    purpose_scope: tuple[str, ...]
    issued_at_wall: str
    issued_at_monotonic_anchor: float
    not_before: str
    expires_at: str
    risk_class: str
    state: str = "DRAFT"
    remaining_uses: Optional[int] = None  # None = unlimited within window
    parent_lease_id: Optional[str] = None
    supersedes_lease_id: Optional[str] = None
    revocation_handle: str = ""
    provenance_refs: tuple[str, ...] = ()
    applied_event_ids: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": LEASE_SCHEMA_VERSION,
            "lease_id": self.lease_id,
            "policy_id": self.policy_id,
            "policy_hash": self.policy_hash,
            "issuer": self.issuer,
            "subject": self.subject,
            "action_scope": list(self.action_scope),
            "object_scope": list(self.object_scope),
            "purpose_scope": list(self.purpose_scope),
            "issued_at_wall": self.issued_at_wall,
            "not_before": self.not_before,
            "expires_at": self.expires_at,
            "risk_class": self.risk_class,
            "state": self.state,
            "remaining_uses": self.remaining_uses,
            "parent_lease_id": self.parent_lease_id,
            "supersedes_lease_id": self.supersedes_lease_id,
            "provenance_refs": list(self.provenance_refs),
        }

    @property
    def lease_hash(self) -> str:
        return canonical_hash(self.to_payload())


def new_lease_id() -> str:
    return f"lease_{uuid.uuid4().hex[:16]}"


def apply_transition(
    lease: CapabilityLease,
    event: str,
    *,
    event_id: str,
    reason_code: str,
    now_wall: str,
    detail: str = "",
) -> tuple[CapabilityLease, Optional[LifecycleEvent]]:
    """Apply one lifecycle event. Idempotent: a previously applied event_id is
    a no-op. Any (state, event) pair not in the table raises. Returns the new
    lease and the LifecycleEvent (None when the event was already applied)."""
    if event_id in lease.applied_event_ids:
        return lease, None
    key = (lease.state, event)
    if key not in TRANSITIONS:
        raise LeaseTransitionError(
            f"invalid transition {lease.state} --{event}--> ? (lease {lease.lease_id})"
        )
    to_state = TRANSITIONS[key]
    updated = replace(
        lease,
        state=to_state,
        applied_event_ids=lease.applied_event_ids + (event_id,),
    )
    lifecycle = LifecycleEvent(
        event_id=event_id,
        lease_id=lease.lease_id,
        event=event,
        from_state=lease.state,
        to_state=to_state,
        reason_code=reason_code,
        at_wall=now_wall,
        detail=detail,
    )
    return updated, lifecycle


def consume_use(lease: CapabilityLease) -> tuple[CapabilityLease, bool]:
    """Decrement remaining uses. Returns (lease, exhausted_now)."""
    if lease.remaining_uses is None:
        return lease, False
    if lease.remaining_uses <= 0:
        return lease, True
    remaining = lease.remaining_uses - 1
    return replace(lease, remaining_uses=remaining), remaining == 0
