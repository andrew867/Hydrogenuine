"""Ownership protocol: offer, accept, decline, renew, release (two-step handoff)."""
from __future__ import annotations
import time
import uuid
from typing import Any, Dict, Optional

from .ownership_ledger import OwnershipLedger
from .ownership_models import OwnershipRecord
from .ownership_store import OwnershipStore


def offer_ownership(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    to: str,
    lease_ttl_s: int,
    ack_deadline_s: int,
    expected_version: int,
    roles_delta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    token_id = str(uuid.uuid4())
    ack_deadline_ts = time.time() + ack_deadline_s
    payload = {
        "token_id": token_id,
        "to": to,
        "lease_ttl_s": lease_ttl_s,
        "ack_deadline_ts": ack_deadline_ts,
        "roles_delta": roles_delta or {},
    }
    ledger.append(task_id, "offer_ownership", actor, payload, expected_version=expected_version)

    def mut(rec: OwnershipRecord):
        rec.state = "assigned"

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err, "token_id": token_id}
    return {"ok": True, "token_id": token_id, "ack_deadline_ts": ack_deadline_ts, "new_version": rec.version}


def accept_ownership(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    token_id: str,
    lease_ttl_s: int,
    expected_version: int,
) -> Dict[str, Any]:
    ledger.append(
        task_id,
        "accept_ownership",
        actor,
        {"token_id": token_id},
        expected_version=expected_version,
    )

    def mut(rec: OwnershipRecord):
        rec.state = "acknowledged"
        rec.current_token_id = token_id
        rec.executor_id = actor
        rec.lease_expires_ts = time.time() + lease_ttl_s

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": rec.version}


def decline_ownership(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    token_id: str,
    reason: str,
    expected_version: int,
) -> Dict[str, Any]:
    ledger.append(
        task_id,
        "decline_ownership",
        actor,
        {"token_id": token_id, "reason": reason},
        expected_version=expected_version,
    )
    # State can stay assigned; offer is declined, sender remains owner
    return {"ok": True}


def renew_lease(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    token_id: str,
    new_ttl_s: int,
    expected_version: int,
) -> Dict[str, Any]:
    new_expiry_ts = time.time() + new_ttl_s
    ledger.append(
        task_id,
        "renew_lease",
        actor,
        {"token_id": token_id, "new_expiry_ts": new_expiry_ts},
        expected_version=expected_version,
    )

    def mut(rec: OwnershipRecord):
        if rec.current_token_id == token_id:
            rec.lease_expires_ts = new_expiry_ts

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": rec.version, "new_expiry_ts": new_expiry_ts}


def release_ownership(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    token_id: str,
    expected_version: int,
    next_offer: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {"token_id": token_id}
    if next_offer is not None:
        payload["next_offer"] = next_offer
    ledger.append(task_id, "release_ownership", actor, payload, expected_version=expected_version)

    def mut(rec: OwnershipRecord):
        if rec.current_token_id == token_id:
            rec.state = "completed"
            rec.current_token_id = ""
            rec.executor_id = ""
            rec.lease_expires_ts = 0.0

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": rec.version}


def set_pending_review(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    approver_spec: Dict[str, Any],
    escalation_spec: Dict[str, Any],
    sla_s: int,
    checkpoint_id: str,
    expected_version: int,
) -> Dict[str, Any]:
    ledger.append(
        task_id,
        "set_pending_review",
        actor,
        {
            "approver_spec": approver_spec,
            "escalation_spec": escalation_spec,
            "sla_s": sla_s,
            "checkpoint_id": checkpoint_id,
        },
        expected_version=expected_version,
    )

    def mut(rec: OwnershipRecord):
        rec.state = "pending_review"
        rec.approver_spec = approver_spec
        rec.escalation_spec = escalation_spec
        rec.checkpoint_id = checkpoint_id

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": rec.version}


def approve_review(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    checkpoint_id: str,
    expected_version: int,
    decision: str = "approved",
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {"checkpoint_id": checkpoint_id, "decision": decision}
    if comment is not None:
        payload["comment"] = comment
    ledger.append(task_id, "approve_review", actor, payload, expected_version=expected_version)

    def mut(rec: OwnershipRecord):
        if rec.checkpoint_id == checkpoint_id:
            rec.state = "in_progress"
            rec.checkpoint_id = None

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": rec.version}


def deny_review(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    checkpoint_id: str,
    expected_version: int,
    decision: str = "denied",
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {"checkpoint_id": checkpoint_id, "decision": decision}
    if comment is not None:
        payload["comment"] = comment
    ledger.append(task_id, "deny_review", actor, payload, expected_version=expected_version)

    def mut(rec: OwnershipRecord):
        if rec.checkpoint_id == checkpoint_id:
            rec.state = "completed"
            rec.checkpoint_id = None

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": rec.version}


def abandon_ownership(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    expected_version: int,
    reason: str = "lease_expired",
) -> Dict[str, Any]:
    """Mark task as abandoned (e.g. after lease expiry). Emits abandonment event."""
    ledger.append(
        task_id,
        "abandoned",
        actor,
        {"reason": reason},
        expected_version=expected_version,
    )

    def mut(rec: OwnershipRecord):
        rec.state = "abandoned"
        rec.executor_id = ""
        rec.current_token_id = ""
        rec.lease_expires_ts = 0.0

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": rec.version}


def mark_contested(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    claims: list,
    expected_version: int,
) -> Dict[str, Any]:
    """Record contested state with claims list (e.g. after CAS conflict)."""
    ledger.append(
        task_id,
        "contested",
        actor,
        {"claims": claims},
        expected_version=expected_version,
    )

    def mut(rec: OwnershipRecord):
        rec.state = "contested"
        rec.contested_claims = claims

    ok, rec, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": rec.version}


def resolve_contested(
    store: OwnershipStore,
    ledger: OwnershipLedger,
    task_id: str,
    actor: str,
    expected_version: int,
    winner_actor: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve contested state. If winner_actor is None, pick deterministically (lexicographically
    smallest actor from contested_claims). Sets state to acknowledged and executor to winner.
    """
    rec = store.get_task(task_id)
    if rec.state != "contested" or not rec.contested_claims:
        return {"ok": False, "error": "NOT_CONTESTED"}
    if rec.version != expected_version:
        return {"ok": False, "error": "VERSION_CONFLICT"}
    winner = winner_actor
    if winner is None:
        winner = min(c.get("actor", "") for c in rec.contested_claims)
    ledger.append(
        task_id,
        "resolve_contested",
        actor,
        {"winner_actor": winner},
        expected_version=expected_version,
    )

    def mut(r: OwnershipRecord):
        r.state = "acknowledged"
        r.executor_id = winner
        claims_snapshot = list(r.contested_claims or [])
        r.contested_claims = None
        for c in claims_snapshot:
            if c.get("actor") == winner:
                r.current_token_id = c.get("token_id", "")
                break

    ok, updated, err = store.cas_update(task_id, expected_version, mut)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "new_version": updated.version, "winner_actor": winner}
