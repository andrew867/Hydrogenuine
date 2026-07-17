"""Operator surface: inspect, explain, revoke, renew, measure saturation.

The system exists to reduce repetitive decisions, not hide decisions. This
module is read-and-revoke only from the authority perspective: nothing here
can broaden a lease. Renewal produces a *draft* that must go back through the
compiler and explicit confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from hg_lease.gpp_bridge import LeaseAuthority
from hg_lease.lease import CapabilityLease
from hg_lease.stores import LeaseStore, ReceiptStore

_REASON_EXPLANATIONS = {
    "lease.none_matching": "no active lease covers this subject/action/object",
    "lease.expired": "the lease's validity window has ended",
    "lease.not_yet_valid": "the lease has not started yet",
    "lease.exhausted": "the lease's allowed number of uses is spent",
    "replay.duplicate_request": "this exact request was already decided once",
    "clock.monotonic_regression": "the system clock moved backwards; failing closed",
    "scope.subject_mismatch": "the requester is not the lease subject",
    "scope.action_mismatch": "the requested action is outside the lease",
    "scope.object_mismatch": "the target object is outside the lease",
    "scope.purpose_mismatch": "the stated purpose is outside the lease",
    "policy.unknown_fact_ask": "a required situation fact is unknown; asking instead of assuming",
}


def _explain_reason(code: str) -> str:
    base = code.split(":", 1)[0]
    if base in _REASON_EXPLANATIONS:
        return _REASON_EXPLANATIONS[base]
    if base.startswith("policy.unknown_fact"):
        return f"situation fact {code.split(':', 1)[-1]!r} is unknown; unknown facts deny"
    if base.startswith("policy.stale_fact"):
        return f"situation fact {code.split(':', 1)[-1]!r} is stale; stale facts deny"
    if base.startswith("policy.condition_false"):
        return "a policy condition is currently not satisfied"
    if base.startswith("policy.outside_time_window"):
        return "the current time is outside the allowed window"
    if base.startswith("limit."):
        return f"a numeric limit was violated ({code})"
    if base.startswith("restriction."):
        return f"a restrictive safety component vetoed execution ({code})"
    if base.startswith("lease.not_active"):
        return f"the lease is not active ({code.split(':', 1)[-1]})"
    return code


@dataclass(frozen=True)
class LeaseView:
    lease_id: str
    state: str
    display_summary: str
    expires_at: str
    remaining_uses: Optional[int]
    risk_class: str
    policy_hash: str


@dataclass(frozen=True)
class SaturationReport:
    """Operator decision saturation: measured, not claimed.

    fresh_confirmations: decisions that required the operator (mints, asks).
    leased_executions: actions executed under a standing lease.
    saturation: confirmations per attempted action (lower is better once a
    lease exists; 1.0 means every action still needs the operator).
    """

    fresh_confirmations: int
    leased_executions: int
    denials: int
    total_attempts: int
    saturation: float


class LeaseDashboard:
    def __init__(
        self,
        *,
        authority: LeaseAuthority,
        lease_store: LeaseStore,
        receipt_store: ReceiptStore,
    ) -> None:
        self._authority = authority
        self._leases = lease_store
        self._receipts = receipt_store

    # ------------------------------------------------------------- inspect --

    def active_leases(self) -> list[LeaseView]:
        views = []
        for lease in self._leases.all():
            if lease.state not in ("ACTIVE", "SUSPENDED"):
                continue
            policy = self._authority.policy_for(lease)
            views.append(
                LeaseView(
                    lease_id=lease.lease_id,
                    state=lease.state,
                    display_summary=policy.display_summary if policy else "(policy unavailable)",
                    expires_at=lease.expires_at,
                    remaining_uses=lease.remaining_uses,
                    risk_class=lease.risk_class,
                    policy_hash=lease.policy_hash,
                )
            )
        return views

    # ------------------------------------------------------------- explain --

    def why_did_you_act(self, receipt_id: str) -> str:
        receipt = self._receipts.get(receipt_id)
        if receipt is None:
            return "No receipt with that id exists."
        outcome = receipt["outcome"]
        if outcome == "ALLOW":
            lease = self._lease_by_hash(receipt.get("lease_hash"))
            policy = self._authority.policy_for(lease) if lease else None
            summary = policy.display_summary if policy else "an operator-confirmed lease"
            return (
                f"I acted because an active lease you confirmed covers this action: "
                f"{summary}. The decision and situation snapshot are recorded in "
                f"receipt {receipt_id}."
            )
        reasons = [r for r in receipt.get("detail", "").split(",") if r]
        explained = "; ".join(_explain_reason(r) for r in reasons) or outcome
        return f"I did not act: {explained} (receipt {receipt_id})."

    def why_did_you_ask(self, reason_codes: tuple[str, ...]) -> str:
        explained = "; ".join(_explain_reason(r) for r in reason_codes)
        return (
            "I asked because I could not reuse standing authority: "
            f"{explained}. Confirming creates or refreshes an explicit lease; "
            "I never act from remembered conversation alone."
        )

    def _lease_by_hash(self, lease_hash: Optional[str]) -> Optional[CapabilityLease]:
        if lease_hash is None:
            return None
        for lease in self._leases.all():
            if lease.lease_hash == lease_hash:
                return lease
        return None

    # -------------------------------------------------------------- revoke --

    def revoke(self, lease_id: str, *, operator_id: str) -> None:
        self._authority.revoke_lease(lease_id, revoker_ref=operator_id)

    def revoke_all(self, *, operator_id: str) -> int:
        return self._authority.revoke_all(revoker_ref=operator_id)

    # ------------------------------------------------------------- renewal --

    def renewal_prompts(self, *, now_wall: str, horizon_wall: str) -> list[dict[str, Any]]:
        """Leases with PROMPT_BEFORE_EXPIRY renewal expiring before horizon."""
        prompts = []
        for lease in self._leases.active():
            policy = self._authority.policy_for(lease)
            if policy is None or policy.renewal_mode != "PROMPT_BEFORE_EXPIRY":
                continue
            if now_wall <= lease.expires_at <= horizon_wall:
                prompts.append(
                    {
                        "lease_id": lease.lease_id,
                        "expires_at": lease.expires_at,
                        "display_summary": policy.display_summary,
                        "renewal_draft": self.renewal_draft(lease.lease_id),
                    }
                )
        return prompts

    def renewal_draft(
        self, lease_id: str, *, changes: Optional[dict[str, Any]] = None
    ) -> Optional[dict[str, Any]]:
        """Build a structured draft to renew a lease, optionally with changed
        conditions. The draft must go through compile_draft and a fresh
        OperatorConfirmation — renewal never silently extends authority."""
        lease = self._leases.get(lease_id)
        policy = self._authority.policy_for(lease) if lease else None
        if lease is None or policy is None:
            return None
        draft: dict[str, Any] = {
            "subjects": list(policy.subjects),
            "actions": list(policy.actions),
            "objects": list(policy.objects),
            "purpose": policy.purpose,
            "risk_class": policy.risk_class,
            "renewal_mode": policy.renewal_mode,
            "unknown_fact_policy": policy.unknown_fact_policy,
            "valid_from": policy.valid_from,
            "valid_until": policy.valid_until,
            "condition": policy.condition.to_payload() if policy.condition else None,
            "numeric_limits": [l.to_payload() for l in policy.numeric_limits],
            "use_limit": policy.use_limit,
            "required_facts": list(policy.required_facts),
            "close_obligations": [dict(o) for o in policy.close_obligations],
            "supersedes_lease_id": lease.lease_id,
        }
        if changes:
            draft.update(changes)
        return draft

    # ---------------------------------------------------------- saturation --

    def saturation_report(self) -> SaturationReport:
        fresh = leased = denials = attempts = 0
        for receipt in self._receipts.all():
            outcome = receipt["outcome"]
            if outcome in ("LEASE_MINTED",):
                fresh += 1
            elif outcome == "ALLOW":
                leased += 1
                attempts += 1
            elif outcome in ("DENY", "ERROR_FAIL_CLOSED"):
                denials += 1
                attempts += 1
            elif outcome == "ASK_REVALIDATE":
                fresh += 1
                attempts += 1
        saturation = (fresh / attempts) if attempts else 0.0
        return SaturationReport(
            fresh_confirmations=fresh,
            leased_executions=leased,
            denials=denials,
            total_attempts=attempts,
            saturation=round(saturation, 4),
        )
