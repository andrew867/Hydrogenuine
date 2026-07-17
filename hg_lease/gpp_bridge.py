"""Lease authority composed over GPP — leases never execute by themselves.

A CapabilityLease is standing, operator-confirmed pre-authorization evidence.
Execution authority is always a short-lived GovernedPermit minted through the
existing hg_gpp.PermitAuthority at the moment of an ALLOW decision. GPP stays
the single authority path; this module adds no second permit system.

Restrictive hooks (AEP/CRR/interlocks) are structurally restrict-only: a hook
may return a deny/ask reason, and its return value can only remove an ALLOW —
there is no code path by which a hook widens scope, extends duration, or
raises limits.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

from hg_gpp.engine import PermitAuthority
from hg_gpp.models import (
    PermitEvidenceRef,
    PermitRequest,
    PermitRevocation,
    PermitScope,
)

from hg_lease.evaluator import (
    ActionRequest,
    Decision,
    OUTCOME_ALLOW,
    OUTCOME_ASK,
    OUTCOME_DENY,
    evaluate,
)
from hg_lease.lease import (
    CapabilityLease,
    apply_transition,
    consume_use,
    new_lease_id,
)
from hg_lease.policy import CanonicalPolicy
from hg_lease.stores import LeaseStore, ReceiptStore, SituationStore

# A restriction hook inspects (request, lease, decision) and returns None to
# stand aside or a reason code string to veto. It cannot grant.
RestrictionHook = Callable[[ActionRequest, CapabilityLease, Decision], Optional[str]]


@dataclass(frozen=True)
class OperatorConfirmation:
    """Explicit operator confirmation of a canonical policy.

    The operator (or their UI) must echo the exact canonical policy hash they
    were shown. A confirmation for a different hash cannot activate a lease.
    """

    operator_id: str
    policy_hash: str
    confirmed_at: str
    display_summary_shown: str


@dataclass(frozen=True)
class AuthorizedAction:
    decision: Decision
    permit_id: Optional[str]
    receipt_id: str
    restriction_results: tuple[str, ...] = ()


class LeaseAuthorityError(RuntimeError):
    pass


class LeaseAuthority:
    """Mints, evaluates, and retires conversational capability leases."""

    def __init__(
        self,
        *,
        permit_authority: PermitAuthority,
        lease_store: LeaseStore,
        receipt_store: ReceiptStore,
        situation_store: SituationStore,
        capability_ref: str,
        effect_class: str,
        authority_chain_ref: str,
        admission_ref: str,
        retention_ref: str,
        agent_id: str,
        clock: Callable[[], tuple[str, float]],
        restriction_hooks: tuple[RestrictionHook, ...] = (),
    ) -> None:
        self._gpp = permit_authority
        self._leases = lease_store
        self._receipts = receipt_store
        self._situation = situation_store
        self._capability_ref = capability_ref
        self._effect_class = effect_class
        self._authority_chain_ref = authority_chain_ref
        self._admission_ref = admission_ref
        self._retention_ref = retention_ref
        self._agent_id = agent_id
        self._clock = clock
        self._hooks = tuple(restriction_hooks)
        self._policies: dict[str, CanonicalPolicy] = {}
        self._seen_request_ids: set[str] = set()
        self._minted_permits: dict[str, list[str]] = {}

    # ------------------------------------------------------------- minting --

    def policy_for(self, lease: CapabilityLease) -> Optional[CanonicalPolicy]:
        return self._policies.get(lease.policy_hash)

    def mint_lease(
        self,
        policy: CanonicalPolicy,
        confirmation: OperatorConfirmation,
        *,
        supersedes_lease_id: Optional[str] = None,
    ) -> CapabilityLease:
        """Mint an ACTIVE lease from an operator-confirmed canonical policy."""
        now_wall, now_mono = self._clock()
        policy_hash = policy.canonical_policy_hash
        if confirmation.policy_hash != policy_hash:
            raise LeaseAuthorityError(
                "confirmation does not match canonical policy hash — refusing to mint"
            )
        if confirmation.operator_id != policy.issuer_operator_id:
            raise LeaseAuthorityError("confirmation operator differs from policy issuer")
        if confirmation.display_summary_shown != policy.display_summary:
            raise LeaseAuthorityError(
                "operator was shown a different summary than the canonical policy"
            )

        lease = CapabilityLease(
            lease_id=new_lease_id(),
            policy_id=policy.policy_id,
            policy_hash=policy_hash,
            issuer=policy.issuer_operator_id,
            subject=policy.subjects[0],
            action_scope=policy.actions,
            object_scope=policy.objects,
            purpose_scope=(policy.purpose,),
            issued_at_wall=now_wall,
            issued_at_monotonic_anchor=now_mono,
            not_before=policy.valid_from,
            expires_at=policy.valid_until,
            risk_class=policy.risk_class,
            remaining_uses=policy.use_limit,
            supersedes_lease_id=supersedes_lease_id,
            revocation_handle=f"rvk_{uuid.uuid4().hex[:12]}",
            provenance_refs=policy.source_conversation_refs,
            state="DRAFT",
        )
        lease, ev1 = apply_transition(
            lease, "submit", event_id=f"{lease.lease_id}:submit",
            reason_code="lease.submitted", now_wall=now_wall,
        )
        lease, ev2 = apply_transition(
            lease, "confirm", event_id=f"{lease.lease_id}:confirm",
            reason_code="lease.operator_confirmed", now_wall=now_wall,
            detail=f"operator={confirmation.operator_id}",
        )
        self._policies[policy_hash] = policy
        self._leases.put(lease, ev1)
        self._leases.put(lease, ev2)

        if supersedes_lease_id:
            self._transition(
                supersedes_lease_id, "supersede",
                reason_code="lease.superseded_by_new_policy",
                detail=f"superseded_by={lease.lease_id}",
            )

        self._receipts.append(
            decision_id=f"mint_{lease.lease_id}",
            outcome="LEASE_MINTED",
            attempted_at=now_wall,
            completed_at=now_wall,
            situation_snapshot_hash=SituationStore.snapshot_hash(
                self._situation.snapshot(now_wall=now_wall)
            ),
            lease_hash=lease.lease_hash,
            policy_hash=policy_hash,
            detail=f"operator={confirmation.operator_id}",
        )
        return lease

    # ---------------------------------------------------------- evaluation --

    def find_lease(self, request: ActionRequest) -> Optional[CapabilityLease]:
        candidates = self._leases.active_for(
            subject=request.subject,
            action_type=request.action_type,
            object_id=request.object_id,
        )
        return candidates[0] if candidates else None

    def authorize(self, request: ActionRequest) -> AuthorizedAction:
        """Evaluate a request; on ALLOW, mint a short-lived GPP permit.

        Every path — allow, deny, ask, error — writes a receipt.
        """
        now_wall, now_mono = self._clock()
        snapshot = self._situation.snapshot(now_wall=now_wall)
        lease = self.find_lease(request)
        policy = self.policy_for(lease) if lease else None

        decision = evaluate(
            request, lease, policy, snapshot,
            now_wall=now_wall, now_monotonic=now_mono,
            seen_request_ids=self._seen_request_ids,
        )
        self._seen_request_ids.add(request.request_id)

        restriction_results: list[str] = []
        if decision.outcome == OUTCOME_ALLOW and lease is not None:
            for hook in self._hooks:
                veto = hook(request, lease, decision)
                if veto is not None:
                    restriction_results.append(veto)
            if restriction_results:
                decision = Decision(
                    decision_id=decision.decision_id,
                    request_id=decision.request_id,
                    outcome=OUTCOME_DENY,
                    lease_id=decision.lease_id,
                    reason_codes=decision.reason_codes
                    + tuple(f"restriction.{r}" for r in restriction_results),
                    situation_snapshot_hash=decision.situation_snapshot_hash,
                    risk_class=decision.risk_class,
                    decision_trace_hash=decision.decision_trace_hash,
                    created_at=decision.created_at,
                )

        permit_id: Optional[str] = None
        if decision.outcome == OUTCOME_ALLOW and lease is not None:
            permit_id = self._mint_execution_permit(request, lease, decision, now_wall)
            if permit_id is None:
                decision = Decision(
                    decision_id=decision.decision_id,
                    request_id=decision.request_id,
                    outcome=OUTCOME_DENY,
                    lease_id=decision.lease_id,
                    reason_codes=decision.reason_codes + ("gpp.permit_denied",),
                    situation_snapshot_hash=decision.situation_snapshot_hash,
                    risk_class=decision.risk_class,
                    decision_trace_hash=decision.decision_trace_hash,
                    created_at=decision.created_at,
                )
            else:
                self._consume(lease, now_wall)

        receipt = self._receipts.append(
            decision_id=decision.decision_id,
            outcome=decision.outcome,
            attempted_at=now_wall,
            situation_snapshot_hash=decision.situation_snapshot_hash,
            lease_hash=lease.lease_hash if lease else None,
            policy_hash=lease.policy_hash if lease else None,
            detail=",".join(decision.reason_codes),
        )
        return AuthorizedAction(
            decision=decision,
            permit_id=permit_id,
            receipt_id=receipt["receipt_id"],
            restriction_results=tuple(restriction_results),
        )

    def _mint_execution_permit(
        self,
        request: ActionRequest,
        lease: CapabilityLease,
        decision: Decision,
        now_wall: str,
    ) -> Optional[str]:
        permit_request = PermitRequest(
            request_id=f"leasex_{request.request_id}",
            subject_id=request.subject,
            agent_id=self._agent_id,
            requested_action_type=request.action_type,
            scope=PermitScope(
                capability_ref=self._capability_ref,
                effect_class=self._effect_class,
                requested_action_type=request.action_type,
                allowed_actions=(request.action_type,),
            ),
            evidence_refs=(
                PermitEvidenceRef(f"lease:{lease.lease_id}", "lease"),
                PermitEvidenceRef(f"trace:{decision.decision_trace_hash}", "decision"),
            ),
            proof_bundle_refs=(f"lease_decision:{decision.decision_id}",),
            identity_ref=lease.issuer,
            admission_ref=self._admission_ref,
            freshness_ref="tim:approval_window_ok",
            redaction_ref="sec:redaction_passed",
            retention_ref=self._retention_ref,
            capability_ref=self._capability_ref,
            risk_class=lease.risk_class.lower(),
            authority_chain_ref=self._authority_chain_ref,
            operator_ref=lease.issuer,
            approval_expires_at=lease.expires_at,
            requestor_id=self._agent_id,
            permit_kind="execute",
        )
        permit_decision = self._gpp.issue(permit_request)
        if permit_decision.status != "granted" or permit_decision.permit is None:
            return None
        self._minted_permits.setdefault(lease.lease_id, []).append(
            permit_decision.permit.permit_id
        )
        return permit_decision.permit.permit_id

    def _consume(self, lease: CapabilityLease, now_wall: str) -> None:
        current = self._leases.get(lease.lease_id)
        if current is None:
            return
        updated, exhausted = consume_use(current)
        self._leases.put(updated)
        if exhausted:
            self._transition(
                updated.lease_id, "exhaust", reason_code="lease.uses_exhausted"
            )

    # ---------------------------------------------------------- lifecycle ---

    def _transition(self, lease_id: str, event: str, *, reason_code: str, detail: str = "") -> None:
        lease = self._leases.get(lease_id)
        if lease is None or lease.state in ("EXPIRED", "EXHAUSTED", "REVOKED", "SUPERSEDED", "FAILED"):
            return
        now_wall, _ = self._clock()
        updated, lifecycle = apply_transition(
            lease, event, event_id=f"{lease_id}:{event}:{uuid.uuid4().hex[:8]}",
            reason_code=reason_code, now_wall=now_wall, detail=detail,
        )
        self._leases.put(updated, lifecycle)

    def suspend_lease(self, lease_id: str, *, reason_code: str) -> None:
        self._transition(lease_id, "suspend", reason_code=reason_code)

    def resume_lease(self, lease_id: str, *, reason_code: str) -> None:
        now_wall, _ = self._clock()
        lease = self._leases.get(lease_id)
        if lease is None:
            return
        if now_wall >= lease.expires_at:
            self._transition(lease_id, "expire", reason_code="lease.expired_during_suspension")
            return
        self._transition(lease_id, "resume", reason_code=reason_code)

    def expire_lease(self, lease_id: str) -> None:
        self._transition(lease_id, "expire", reason_code="lease.window_elapsed")

    def revoke_lease(self, lease_id: str, *, revoker_ref: str, reason_code: str = "lease.operator_revoked") -> None:
        """Revoke one lease and every outstanding permit minted from it."""
        self._transition(lease_id, "revoke", reason_code=reason_code, detail=f"revoker={revoker_ref}")
        now_wall, _ = self._clock()
        for permit_id in self._minted_permits.get(lease_id, []):
            self._gpp.revoke(
                PermitRevocation(
                    permit_id=permit_id,
                    revoked_at=now_wall,
                    reason_code=reason_code,
                    revoker_ref=revoker_ref,
                )
            )
        self._receipts.append(
            decision_id=f"revoke_{lease_id}",
            outcome="LEASE_REVOKED",
            attempted_at=now_wall,
            completed_at=now_wall,
            situation_snapshot_hash=SituationStore.snapshot_hash(
                self._situation.snapshot(now_wall=now_wall)
            ),
            detail=f"revoker={revoker_ref};reason={reason_code}",
        )

    def revoke_all(self, *, revoker_ref: str) -> int:
        active = [l.lease_id for l in self._leases.all() if l.state in ("ACTIVE", "SUSPENDED")]
        for lease_id in active:
            self.revoke_lease(lease_id, revoker_ref=revoker_ref, reason_code="lease.revoke_all")
        return len(active)
