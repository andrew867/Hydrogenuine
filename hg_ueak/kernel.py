"""UEAK execution authority kernel — single admission choke point."""

from __future__ import annotations

from typing import Any, Callable, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.time.clock import get_clock
from hg_gpp.store import PermitStore

from hg_ueak.dispatch import FakeDispatchSink
from hg_ueak.models import (
    ExecutionAdmissionDecision,
    ExecutionDispatchPlan,
    ExecutionReceipt,
    ExecutionRefusalReason,
    ExecutionRequest,
    PermitBinding,
)
from hg_ueak.validation import validate_execution_request

_UEAK_ISSUER = "ueak:execution_authority"


def _utc_now() -> str:
    return get_clock().now_utc()


class ExecutionAuthorityKernel:
    """UEAK runtime — validates authority chain and admits to governed dispatch surface."""

    issuer_id: str = _UEAK_ISSUER

    def __init__(
        self,
        *,
        permit_store: Optional[PermitStore] = None,
        dispatch_sink: Optional[FakeDispatchSink] = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._permit_store = permit_store or PermitStore()
        self._dispatch = dispatch_sink or FakeDispatchSink()
        self._clock = clock or _utc_now
        self._admission_log: list[dict[str, Any]] = []
        self._processed_keys: set[str] = set()

    @property
    def permit_store(self) -> PermitStore:
        return self._permit_store

    @property
    def dispatch_sink(self) -> FakeDispatchSink:
        return self._dispatch

    @property
    def admission_log(self) -> list[dict[str, Any]]:
        return list(self._admission_log)

    def now(self) -> str:
        return self._clock()

    def admit(self, request: ExecutionRequest) -> ExecutionAdmissionDecision:
        """Validate and admit or refuse — never mints permits."""
        now = self.now()
        idem = request.idempotency_key or request.request_id
        if idem in self._processed_keys:
            return self._refuse(
                request,
                [ExecutionRefusalReason("ueak.denied.duplicate", "duplicate idempotency key")],
                now=now,
            )

        reasons = validate_execution_request(request, now=now, permit_store=self._permit_store)
        if reasons:
            return self._refuse(request, reasons, now=now)

        permit = request.permit
        assert permit is not None
        binding = PermitBinding(
            permit_id=permit.permit_id,
            permit_hash=permit.permit_hash,
            capability_ref=permit.capability_ref,
            effect_class=permit.scope.effect_class,
        )
        dispatch_id = f"disp_{canonical_hash(request.request_id + now)[7:19]}"
        plan = ExecutionDispatchPlan(
            dispatch_id=dispatch_id,
            request_id=request.request_id,
            candidate_id=request.candidate.candidate_id,
            capability_id=request.candidate.capability_id,
            effect_class=request.candidate.effect_class,
            permit_binding=binding,
        )
        self._dispatch.dispatch(plan)
        self._processed_keys.add(idem)

        receipt = ExecutionReceipt(
            receipt_id=f"ueak_rcpt_{canonical_hash({'request_id': request.request_id, 'status': 'admitted', 'now': now})[7:19]}",
            request_id=request.request_id,
            status="admitted",
            permit_id=permit.permit_id,
            issued_at=now,
            dispatch_id=dispatch_id,
        )
        decision = ExecutionAdmissionDecision(
            status="admitted",
            request_id=request.request_id,
            dispatch_plan=plan,
            receipt=receipt,
        )
        self._admission_log.append(
            {
                "event": "ueak.admitted",
                "request_id": request.request_id,
                "dispatch_id": dispatch_id,
                "receipt_hash": receipt.receipt_hash,
            }
        )
        return decision

    def _refuse(
        self,
        request: ExecutionRequest,
        reasons: list[ExecutionRefusalReason],
        *,
        now: str,
    ) -> ExecutionAdmissionDecision:
        permit_id = request.permit.permit_id if request.permit else ""
        receipt = ExecutionReceipt(
            receipt_id=f"ueak_rcpt_{canonical_hash({'request_id': request.request_id, 'status': 'refused', 'now': now, 'reasons': [r.code for r in reasons]})[7:19]}",
            request_id=request.request_id,
            status="refused",
            permit_id=permit_id,
            issued_at=now,
            refusal_reasons=tuple(reasons),
        )
        self._admission_log.append(
            {
                "event": "ueak.refused",
                "request_id": request.request_id,
                "reasons": [r.code for r in reasons],
            }
        )
        return ExecutionAdmissionDecision(
            status="refused",
            request_id=request.request_id,
            receipt=receipt,
            refusal_reasons=tuple(reasons),
        )


__all__ = ["ExecutionAuthorityKernel", "_UEAK_ISSUER"]
