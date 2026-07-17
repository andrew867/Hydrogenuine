"""GPP permit binder — permission binding only; no execution dispatch."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable, Mapping, Optional

from hg_core.governance.capability_registry import lookup_capability, lookup_decision
from hg_core.governance.trace_emitter import TraceEmitter
from hg_core.governance.types import (
    BindRequest,
    BindResult,
    BindValidationError,
    DenyRecord,
    Permit,
    TraceRef,
)

DEFAULT_PERMIT_TTL_S = 30


@dataclass
class PermitBinder:
    """
    Binds an explicit decision reference and capability descriptor to a permit
    or deny record. Records trace evidence only; never dispatches actions.
    """

    trace_emitter: Optional[TraceEmitter] = None
    clock: Optional[Callable[[], str]] = None
    permit_ttl_s: int = DEFAULT_PERMIT_TTL_S

    def bind(
        self,
        request: BindRequest,
        capability_descriptor: Mapping[str, str],
        trace_ref: Optional[TraceRef] = None,
        *,
        run_id: str = "gpp-bind",
        workflow_id: str = "gpp-phase1",
    ) -> BindResult:
        if request.capability_id != capability_descriptor.get("capability_id"):
            raise BindValidationError("request capability_id does not match descriptor")
        if request.effect_class != capability_descriptor.get("effect_class"):
            raise BindValidationError("request effect_class does not match descriptor")

        decision = lookup_decision(request.decision_ref)
        if decision is None:
            deny, trace_record = self._deny(
                request,
                reason_code="unknown_decision_ref",
                trace_ref=trace_ref,
            )
            return BindResult(outcome="deny", deny=deny, trace_record=trace_record)

        capability = lookup_capability(request.capability_id)
        if capability is None:
            deny, trace_record = self._deny(
                request, reason_code="unknown_capability", trace_ref=trace_ref
            )
            return BindResult(outcome="deny", deny=deny, trace_record=trace_record)

        if capability.effect_class != request.effect_class:
            deny, trace_record = self._deny(
                request, reason_code="effect_class_mismatch", trace_ref=trace_ref
            )
            return BindResult(outcome="deny", deny=deny, trace_record=trace_record)

        if not capability.bind_allowed:
            deny, trace_record = self._deny(
                request, reason_code="capability_denied", trace_ref=trace_ref
            )
            return BindResult(outcome="deny", deny=deny, trace_record=trace_record)

        if decision.verdict != "allow":
            deny, trace_record = self._deny(
                request,
                reason_code=decision.reason_code or "decision_denied",
                trace_ref=trace_ref,
            )
            return BindResult(outcome="deny", deny=deny, trace_record=trace_record)

        trace_record = None
        resolved_trace = trace_ref
        if self.trace_emitter is not None:
            trace_record = self.trace_emitter.emit(
                run_id=run_id,
                workflow_id=workflow_id,
                layer="governance",
                component="gpp_permit_binder",
                event="permit_bound",
                decision="allow",
                reason_code="permit_scaffold",
                summary=f"GPP permit scaffold bound for {request.request_id}",
                subject={
                    "type": "gpp_bind_request",
                    "request_id": request.request_id,
                    "capability_id": request.capability_id,
                },
                inputs={
                    "request_id": request.request_id,
                    "capability_id": request.capability_id,
                    "effect_class": request.effect_class,
                    "decision_ref": request.decision_ref,
                },
                outputs={"outcome": "permit"},
                external_calls=0,
                metadata={"phase": "gpp_phase1_scaffold"},
            )
            if trace_record is not None:
                resolved_trace = TraceRef(
                    trace_path=str(self.trace_emitter.path),
                    trace_seq=int(trace_record["seq"]),
                    trace_event_hash=str(trace_record["event_hash"]),
                )

        if resolved_trace is None:
            deny, trace_record = self._deny(
                request, reason_code="missing_trace_ref", trace_ref=None
            )
            return BindResult(outcome="deny", deny=deny, trace_record=trace_record)

        permit = Permit(
            permit_id=f"gpp_perm_{uuid.uuid4().hex[:16]}",
            request_id=request.request_id,
            capability_id=request.capability_id,
            effect_class=request.effect_class,
            issued_at=self._now(),
            expires_at=None,
            decision_ref=request.decision_ref,
            trace_ref=resolved_trace,
        )
        return BindResult(outcome="permit", permit=permit, trace_record=trace_record)

    def _deny(
        self,
        request: BindRequest,
        *,
        reason_code: str,
        trace_ref: Optional[TraceRef],
    ) -> tuple[DenyRecord, Optional[Mapping]]:
        trace_record = None
        if self.trace_emitter is not None:
            trace_record = self.trace_emitter.emit(
                run_id="gpp-bind",
                workflow_id="gpp-phase1",
                layer="governance",
                component="gpp_permit_binder",
                event="publish_blocked",
                decision="deny",
                reason_code=reason_code,
                summary=f"GPP bind denied for {request.request_id}: {reason_code}",
                subject={
                    "type": "gpp_bind_request",
                    "request_id": request.request_id,
                },
                inputs={
                    "request_id": request.request_id,
                    "capability_id": request.capability_id,
                    "effect_class": request.effect_class,
                    "decision_ref": request.decision_ref,
                },
                external_calls=0,
                metadata={"phase": "gpp_phase1_scaffold"},
            )
            if trace_record is not None and trace_ref is None:
                trace_ref = TraceRef(
                    trace_path=str(self.trace_emitter.path),
                    trace_seq=int(trace_record["seq"]),
                    trace_event_hash=str(trace_record["event_hash"]),
                )
        deny = DenyRecord(
            request_id=request.request_id,
            capability_id=request.capability_id,
            effect_class=request.effect_class,
            reason_code=reason_code,
            decision_ref=request.decision_ref,
            denied_at=self._now(),
            trace_ref=trace_ref,
        )
        return deny, trace_record

    def _now(self) -> str:
        if self.clock is not None:
            return self.clock()
        from hg_core.governance.trace_emitter import _utcnow_iso

        return _utcnow_iso()


def descriptor_for(capability_id: str) -> Mapping[str, str]:
    capability = lookup_capability(capability_id)
    if capability is None:
        raise BindValidationError(f"unknown capability {capability_id!r}")
    return {
        "capability_id": capability.capability_id,
        "effect_class": capability.effect_class,
    }


__all__ = ["PermitBinder", "descriptor_for", "DEFAULT_PERMIT_TTL_S"]
