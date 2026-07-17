"""Multi-operator roles, conflict handling, delegation without amplification.

Role model: OWNER > HOUSEHOLD_MEMBER > GUEST > SERVICE. Device-local policy is
a restrict-only overlay that can deny anything regardless of role. Conflicts
resolve deny-wins: any applicable prohibition from an equal-or-higher role
defeats any allow.

Delegation derives a child lease strictly inside the parent's envelope:
subset scopes, non-later expiry, non-greater uses, non-wider limits. Any
attempt to exceed the parent fails closed. Guests and services cannot
delegate further.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional

from hg_lease.lease import CapabilityLease, apply_transition, new_lease_id
from hg_lease.stores import LeaseStore

ROLE_OWNER = "OWNER"
ROLE_MEMBER = "HOUSEHOLD_MEMBER"
ROLE_GUEST = "GUEST"
ROLE_SERVICE = "SERVICE"

_ROLE_RANK = {ROLE_OWNER: 3, ROLE_MEMBER: 2, ROLE_GUEST: 1, ROLE_SERVICE: 1}
_MAY_DELEGATE = {ROLE_OWNER, ROLE_MEMBER}


class DelegationError(RuntimeError):
    """Refused delegation — fail closed."""


@dataclass(frozen=True)
class Prohibition:
    """A standing 'do not' from an operator or device-local policy."""

    issuer_id: str
    issuer_role: str
    action_type: str
    object_id: str
    reason: str = ""
    device_local: bool = False


def resolve_conflict(
    *,
    lease_issuer_role: str,
    prohibitions: list[Prohibition],
    action_type: str,
    object_id: str,
) -> Optional[str]:
    """Return a deny reason when a prohibition defeats the lease, else None.

    Deny wins whenever the prohibiting party is device-local policy or has
    role rank >= the lease issuer's rank. A guest's prohibition cannot defeat
    an owner's lease, but an owner's prohibition defeats everything.
    """
    lease_rank = _ROLE_RANK.get(lease_issuer_role, 0)
    for p in prohibitions:
        if p.action_type != action_type or p.object_id != object_id:
            continue
        if p.device_local:
            return f"conflict.device_local_policy:{p.issuer_id}"
        if _ROLE_RANK.get(p.issuer_role, 0) >= lease_rank:
            return f"conflict.prohibited_by:{p.issuer_id}"
    return None


def _subset(child: tuple[str, ...], parent: tuple[str, ...], label: str) -> tuple[str, ...]:
    extra = set(child) - set(parent)
    if extra:
        raise DelegationError(f"delegation.scope_amplification:{label}:{sorted(extra)}")
    if not child:
        raise DelegationError(f"delegation.empty_scope:{label}")
    return tuple(child)


def delegate_lease(
    *,
    parent: CapabilityLease,
    parent_issuer_role: str,
    delegate_subject: str,
    lease_store: LeaseStore,
    now_wall: str,
    now_monotonic: float,
    action_scope: Optional[tuple[str, ...]] = None,
    object_scope: Optional[tuple[str, ...]] = None,
    purpose_scope: Optional[tuple[str, ...]] = None,
    expires_at: Optional[str] = None,
    remaining_uses: Optional[int] = None,
) -> CapabilityLease:
    """Derive a child lease strictly within the parent envelope."""
    if parent_issuer_role not in _MAY_DELEGATE:
        raise DelegationError(f"delegation.role_may_not_delegate:{parent_issuer_role}")
    if parent.state != "ACTIVE":
        raise DelegationError(f"delegation.parent_not_active:{parent.state}")
    if parent.parent_lease_id is not None:
        # One level only: re-delegation of delegated authority is amplification
        # of reach even when scopes shrink.
        raise DelegationError("delegation.no_redelegation")

    child_expiry = expires_at or parent.expires_at
    if child_expiry > parent.expires_at:
        raise DelegationError("delegation.duration_amplification")
    if child_expiry <= now_wall:
        raise DelegationError("delegation.already_expired")

    if parent.remaining_uses is not None:
        if remaining_uses is None or remaining_uses > parent.remaining_uses:
            raise DelegationError("delegation.use_amplification")

    child = CapabilityLease(
        lease_id=new_lease_id(),
        policy_id=parent.policy_id,
        policy_hash=parent.policy_hash,
        issuer=parent.issuer,
        subject=delegate_subject,
        action_scope=_subset(action_scope or parent.action_scope, parent.action_scope, "actions"),
        object_scope=_subset(object_scope or parent.object_scope, parent.object_scope, "objects"),
        purpose_scope=_subset(purpose_scope or parent.purpose_scope, parent.purpose_scope, "purpose"),
        issued_at_wall=now_wall,
        issued_at_monotonic_anchor=now_monotonic,
        not_before=max(parent.not_before, now_wall),
        expires_at=child_expiry,
        risk_class=parent.risk_class,
        remaining_uses=remaining_uses if parent.remaining_uses is not None else remaining_uses,
        parent_lease_id=parent.lease_id,
        revocation_handle=f"rvk_{uuid.uuid4().hex[:12]}",
        provenance_refs=parent.provenance_refs + (f"delegated_from:{parent.lease_id}",),
        state="DRAFT",
    )
    child, ev1 = apply_transition(
        child, "submit", event_id=f"{child.lease_id}:submit",
        reason_code="delegation.submitted", now_wall=now_wall,
    )
    child, ev2 = apply_transition(
        child, "confirm", event_id=f"{child.lease_id}:confirm",
        reason_code="delegation.derived_from_parent", now_wall=now_wall,
        detail=f"parent={parent.lease_id}",
    )
    lease_store.put(child, ev1)
    lease_store.put(child, ev2)
    return child


def revoke_delegations_of(
    parent_lease_id: str, *, lease_store: LeaseStore, now_wall: str
) -> list[str]:
    """Parent revocation cascades to every child lease."""
    revoked = []
    for lease in lease_store.all():
        if lease.parent_lease_id != parent_lease_id:
            continue
        if lease.state in ("ACTIVE", "SUSPENDED"):
            updated, event = apply_transition(
                lease, "revoke",
                event_id=f"{lease.lease_id}:cascade:{uuid.uuid4().hex[:8]}",
                reason_code="delegation.parent_revoked", now_wall=now_wall,
            )
            lease_store.put(updated, event)
            revoked.append(lease.lease_id)
    return revoked
