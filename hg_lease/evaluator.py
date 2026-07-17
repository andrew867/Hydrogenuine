"""Deterministic lease evaluator (hg.decision.v1).

A pure function of (action request, lease, policy, situation snapshot, clock).
No model output, no randomness, no I/O. The decision trace hash makes any
decision reproducible from its recorded inputs. Everything ambiguous fails
closed: unknown facts, stale facts, unit mismatches, clock regression, and
duplicate request ids all deny.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash

from hg_lease.lease import CapabilityLease
from hg_lease.policy import CanonicalPolicy, EvalContext
from hg_lease.stores import SituationFact, SituationStore

DECISION_SCHEMA_VERSION = "hg.decision.v1"

OUTCOME_ALLOW = "ALLOW"
OUTCOME_DENY = "DENY"
OUTCOME_ASK = "ASK_REVALIDATE"
OUTCOME_ERROR = "ERROR_FAIL_CLOSED"

REASON_LEASE_NOT_ACTIVE = "lease.not_active"
REASON_LEASE_NOT_YET_VALID = "lease.not_yet_valid"
REASON_LEASE_EXPIRED = "lease.expired"
REASON_LEASE_EXHAUSTED = "lease.exhausted"
REASON_POLICY_HASH_MISMATCH = "lease.policy_hash_mismatch"
REASON_SCOPE_SUBJECT = "scope.subject_mismatch"
REASON_SCOPE_ACTION = "scope.action_mismatch"
REASON_SCOPE_OBJECT = "scope.object_mismatch"
REASON_SCOPE_PURPOSE = "scope.purpose_mismatch"
REASON_CLOCK_REGRESSION = "clock.monotonic_regression"
REASON_REPLAY = "replay.duplicate_request"
REASON_UNKNOWN_FACT_ASK = "policy.unknown_fact_ask"


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    subject: str
    action_type: str
    object_id: str
    purpose: str
    requested_at: str
    parameters: dict[str, Any] = field(default_factory=dict)
    context_refs: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "hg.action.v1",
            "request_id": self.request_id,
            "subject": self.subject,
            "action_type": self.action_type,
            "object_id": self.object_id,
            "purpose": self.purpose,
            "parameters": dict(self.parameters),
            "requested_at": self.requested_at,
            "context_refs": list(self.context_refs),
        }


@dataclass(frozen=True)
class Decision:
    decision_id: str
    request_id: str
    outcome: str
    lease_id: Optional[str]
    reason_codes: tuple[str, ...]
    situation_snapshot_hash: str
    risk_class: str
    decision_trace_hash: str
    created_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": DECISION_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "outcome": self.outcome,
            "lease_id": self.lease_id,
            "reason_codes": list(self.reason_codes),
            "situation_snapshot_hash": self.situation_snapshot_hash,
            "risk_class": self.risk_class,
            "decision_trace_hash": self.decision_trace_hash,
            "created_at": self.created_at,
        }


def _decision(
    *,
    request: ActionRequest,
    outcome: str,
    reasons: list[str],
    lease: Optional[CapabilityLease],
    snapshot_hash: str,
    now_wall: str,
) -> Decision:
    trace = {
        "request": request.to_payload(),
        "lease_id": lease.lease_id if lease else None,
        "lease_hash": lease.lease_hash if lease else None,
        "outcome": outcome,
        "reason_codes": sorted(reasons),
        "situation_snapshot_hash": snapshot_hash,
        "now_wall": now_wall,
    }
    return Decision(
        decision_id=f"dec_{uuid.uuid4().hex[:16]}",
        request_id=request.request_id,
        outcome=outcome,
        lease_id=lease.lease_id if lease else None,
        reason_codes=tuple(sorted(reasons)),
        situation_snapshot_hash=snapshot_hash,
        risk_class=lease.risk_class if lease else "UNKNOWN",
        decision_trace_hash=canonical_hash(trace),
        created_at=now_wall,
    )


def evaluate(
    request: ActionRequest,
    lease: Optional[CapabilityLease],
    policy: Optional[CanonicalPolicy],
    snapshot: dict[str, SituationFact],
    *,
    now_wall: str,
    now_monotonic: float,
    seen_request_ids: Optional[set[str]] = None,
) -> Decision:
    """Evaluate one action request against one lease. Deny by default."""
    snapshot_hash = SituationStore.snapshot_hash(snapshot)
    reasons: list[str] = []

    if seen_request_ids is not None and request.request_id in seen_request_ids:
        return _decision(
            request=request, outcome=OUTCOME_DENY, reasons=[REASON_REPLAY],
            lease=lease, snapshot_hash=snapshot_hash, now_wall=now_wall,
        )

    if lease is None or policy is None:
        return _decision(
            request=request, outcome=OUTCOME_DENY, reasons=["lease.none_matching"],
            lease=lease, snapshot_hash=snapshot_hash, now_wall=now_wall,
        )

    # Clock sanity: monotonic time must not run backwards relative to the
    # lease anchor. Ambiguous time fails closed.
    if now_monotonic < lease.issued_at_monotonic_anchor:
        return _decision(
            request=request, outcome=OUTCOME_ERROR, reasons=[REASON_CLOCK_REGRESSION],
            lease=lease, snapshot_hash=snapshot_hash, now_wall=now_wall,
        )

    if lease.policy_hash != policy.canonical_policy_hash:
        return _decision(
            request=request, outcome=OUTCOME_ERROR, reasons=[REASON_POLICY_HASH_MISMATCH],
            lease=lease, snapshot_hash=snapshot_hash, now_wall=now_wall,
        )

    if lease.state != "ACTIVE":
        reasons.append(f"{REASON_LEASE_NOT_ACTIVE}:{lease.state}")

    if now_wall < lease.not_before:
        reasons.append(REASON_LEASE_NOT_YET_VALID)
    if now_wall >= lease.expires_at:
        reasons.append(REASON_LEASE_EXPIRED)

    if lease.remaining_uses is not None and lease.remaining_uses <= 0:
        reasons.append(REASON_LEASE_EXHAUSTED)

    if request.subject != lease.subject:
        reasons.append(REASON_SCOPE_SUBJECT)
    if request.action_type not in lease.action_scope:
        reasons.append(REASON_SCOPE_ACTION)
    if request.object_id not in lease.object_scope:
        reasons.append(REASON_SCOPE_OBJECT)
    if lease.purpose_scope and request.purpose not in lease.purpose_scope:
        reasons.append(REASON_SCOPE_PURPOSE)

    for limit in policy.numeric_limits:
        res = limit.check(request.parameters)
        if not res.ok:
            reasons.extend(res.reasons)

    unknown_ask = False
    if policy.condition is not None:
        ctx = EvalContext(facts=dict(snapshot), now_wall=now_wall)
        res = policy.condition.evaluate(ctx)
        if not res.ok:
            cond_reasons = list(res.reasons)
            if policy.unknown_fact_policy == "ASK" and all(
                r.startswith("policy.unknown_fact") for r in cond_reasons
            ) and cond_reasons:
                unknown_ask = True
                reasons.append(REASON_UNKNOWN_FACT_ASK)
            else:
                reasons.extend(cond_reasons)

    for fact_name in policy.required_facts:
        if fact_name not in snapshot:
            reasons.append(f"policy.required_fact_missing:{fact_name}")

    if not reasons:
        outcome = OUTCOME_ALLOW
    elif unknown_ask and len(reasons) == 1:
        outcome = OUTCOME_ASK
    else:
        outcome = OUTCOME_DENY
    return _decision(
        request=request, outcome=outcome, reasons=reasons,
        lease=lease, snapshot_hash=snapshot_hash, now_wall=now_wall,
    )
