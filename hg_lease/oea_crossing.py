"""Lease-governed external-action crossing.

The single funnel from "an agent wants to act" to "a simulated device does
something". Order of authority:

  1. LeaseAuthority.authorize — deterministic lease/situation evaluation,
     restrictive vetoes, and (on ALLOW) a short-lived GovernedPermit minted
     through hg_gpp;
  2. verify_permit + single-use consume against the GPP store — an adapter,
     model, memory module, or tool cannot self-authorize, and a permit cannot
     be replayed;
  3. adapter dispatch through the registry (simulated unless hardware is
     explicitly configured);
  4. a final decision record carrying intent match, lease match, situation
     match, veto results, risk class, OEA result, and receipt id — plus an
     execution receipt appended to the same chain as the decision receipt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_gpp.engine import PermitAuthority
from hg_gpp.verifier import verify_permit

from hg_lease.adapters import AdapterRegistry
from hg_lease.evaluator import ActionRequest, OUTCOME_ALLOW
from hg_lease.gpp_bridge import LeaseAuthority
from hg_lease.stores import ReceiptStore


@dataclass(frozen=True)
class CrossingResult:
    outcome: str  # EXECUTED | REFUSED | PERMIT_REJECTED | ADAPTER_FAILED
    decision_outcome: str
    reason_codes: tuple[str, ...]
    lease_id: Optional[str]
    permit_id: Optional[str]
    risk_class: str
    situation_snapshot_hash: str
    decision_trace_hash: str
    restriction_results: tuple[str, ...]
    receipt_id: str
    execution_receipt_id: Optional[str]
    adapter_result: Optional[dict[str, Any]]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "hg.crossing.decision.v1",
            "outcome": self.outcome,
            "decision_outcome": self.decision_outcome,
            "reason_codes": list(self.reason_codes),
            "lease_id": self.lease_id,
            "permit_id": self.permit_id,
            "risk_class": self.risk_class,
            "situation_snapshot_hash": self.situation_snapshot_hash,
            "decision_trace_hash": self.decision_trace_hash,
            "restriction_results": list(self.restriction_results),
            "receipt_id": self.receipt_id,
            "execution_receipt_id": self.execution_receipt_id,
            "adapter_result": self.adapter_result,
        }


class LeaseCrossing:
    def __init__(
        self,
        *,
        authority: LeaseAuthority,
        permit_authority: PermitAuthority,
        registry: AdapterRegistry,
        receipt_store: ReceiptStore,
        capability_ref: str,
        effect_class: str,
        clock,
    ) -> None:
        self._authority = authority
        self._gpp = permit_authority
        self._registry = registry
        self._receipts = receipt_store
        self._capability_ref = capability_ref
        self._effect_class = effect_class
        self._clock = clock

    def request_action(self, request: ActionRequest) -> CrossingResult:
        authorized = self._authority.authorize(request)
        decision = authorized.decision

        base = dict(
            decision_outcome=decision.outcome,
            reason_codes=decision.reason_codes,
            lease_id=decision.lease_id,
            permit_id=authorized.permit_id,
            risk_class=decision.risk_class,
            situation_snapshot_hash=decision.situation_snapshot_hash,
            decision_trace_hash=decision.decision_trace_hash,
            restriction_results=authorized.restriction_results,
            receipt_id=authorized.receipt_id,
        )

        if decision.outcome != OUTCOME_ALLOW or authorized.permit_id is None:
            return CrossingResult(
                outcome="REFUSED", execution_receipt_id=None, adapter_result=None, **base
            )

        now_wall, _ = self._clock()
        permit = self._gpp.store.get(authorized.permit_id)
        ok, reason = (False, "gpp.denied.invalid_status") if permit is None else verify_permit(
            permit,
            now=now_wall,
            store=self._gpp.store,
            action_type=request.action_type,
            capability_ref=self._capability_ref,
            effect_class=self._effect_class,
        )
        if ok:
            consume = self._gpp.store.consume(
                authorized.permit_id, now=now_wall, consumed_by="lease_crossing"
            )
            if not consume.ok:
                ok, reason = False, consume.reason or "gpp.denied.consume_failed"
        if not ok:
            execution_receipt = self._append_execution_receipt(
                decision, request, outcome="PERMIT_REJECTED", detail=reason, now_wall=now_wall
            )
            return CrossingResult(
                outcome="PERMIT_REJECTED",
                execution_receipt_id=execution_receipt["receipt_id"],
                adapter_result=None,
                **{**base, "reason_codes": decision.reason_codes + (reason,)},
            )

        adapter = self._registry.for_device(request.object_id, request.action_type)
        if adapter is None:
            execution_receipt = self._append_execution_receipt(
                decision, request, outcome="ADAPTER_FAILED",
                detail="no adapter for device/action", now_wall=now_wall,
            )
            return CrossingResult(
                outcome="ADAPTER_FAILED",
                execution_receipt_id=execution_receipt["receipt_id"],
                adapter_result=None,
                **{**base, "reason_codes": decision.reason_codes + ("adapter.none_registered",)},
            )

        result = adapter.perform(
            device_id=request.object_id,
            action_type=request.action_type,
            parameters=request.parameters,
        )
        outcome = "EXECUTED" if result.ok else "ADAPTER_FAILED"
        execution_receipt = self._append_execution_receipt(
            decision, request, outcome=outcome,
            detail="", now_wall=now_wall, adapter_result=result.to_payload(),
        )
        return CrossingResult(
            outcome=outcome,
            execution_receipt_id=execution_receipt["receipt_id"],
            adapter_result=result.to_payload(),
            **base,
        )

    def _append_execution_receipt(
        self,
        decision,
        request: ActionRequest,
        *,
        outcome: str,
        detail: str,
        now_wall: str,
        adapter_result: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return self._receipts.append(
            decision_id=decision.decision_id,
            outcome=outcome,
            attempted_at=request.requested_at,
            completed_at=now_wall,
            situation_snapshot_hash=decision.situation_snapshot_hash,
            adapter_request_hash=canonical_hash(request.to_payload()),
            adapter_result_hash=canonical_hash(adapter_result) if adapter_result else None,
            detail=detail,
        )
