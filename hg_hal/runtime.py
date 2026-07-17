"""HAL event-sourced runtime — arbitrate and route; never mint or execute."""

from __future__ import annotations

from typing import Any, Callable, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.time.clock import get_clock

from hg_hal.arbitration import arbitrate
from hg_hal.event_log import HalEventLogAdapter
from hg_hal.events import (
    HAL_ARBITRATION_STARTED,
    HAL_AUTHORITY_CONVERSION_CONTAINED,
    HAL_CONTEXT_BUILT,
    HAL_DECISION_PROPOSED,
    HAL_DEGRADED_MODE_ENTERED,
    HAL_FAILED_CLOSED,
    HAL_GPP_ROUTE_REQUESTED,
    HAL_OPERATOR_REVIEW_REQUESTED,
    HAL_PANIC_ENTERED,
    HAL_REJECTED,
    HAL_REPLAY_VERIFIED,
    HAL_REQUEST_RECEIVED,
    HAL_ROUTE_SELECTED,
    HAL_UEAK_ROUTE_REQUESTED,
)
from hg_hal.models import (
    HalArbitrationContext,
    HalDecision,
    HalDecisionReason,
    HalDecisionState,
    HalDegradedMode,
    HalEvent,
    HalPanicState,
    HalRequest,
    HalRoute,
    HalRuntimeState,
)
from hg_hal.reducer import HalReducer
from hg_hal.state import initial_state
from hg_hal.types import ArbitrationResult
from hg_hal.validation import (
    DENIED_DEGRADED_ROUTE,
    DENIED_DUPLICATE,
    DENIED_PANIC_ACTIVE,
    DENIED_UEAK_DIRECT,
    validate_hal_request,
)


def _utc_now() -> str:
    return get_clock().now_utc()


def _map_result_to_decision(
    result: ArbitrationResult,
    *,
    request: HalRequest,
    contradictions: tuple[str, ...],
    degraded_active: bool,
) -> tuple[HalDecisionState, HalRoute, list[HalDecisionReason]]:
    reasons: list[HalDecisionReason] = []
    if result.routing == "ACCEPT":
        if degraded_active:
            return (
                "route_to_operator",
                HalRoute(target="operator", route_ref=f"hal:operator:{request.arbitration.request_id}", decision_state="route_to_operator"),
                [HalDecisionReason(DENIED_DEGRADED_ROUTE, "degraded mode routes to operator only")],
            )
        return (
            "route_to_GPP",
            HalRoute(target="GPP", route_ref=f"hal:gpp:{request.arbitration.request_id}", decision_state="route_to_GPP"),
            reasons,
        )
    if result.routing == "DEFER":
        return (
            "defer",
            HalRoute(target="none", route_ref=f"hal:defer:{request.arbitration.request_id}", decision_state="defer"),
            [HalDecisionReason("hal.defer.candidate", result.reason_code)],
        )
    if result.routing == "REJECT":
        state: HalDecisionState = "reject"
        if result.reason_code in {"soar_binding_reject", "capability_denied"}:
            state = "request_clarification"
        return (
            state,
            HalRoute(target="none", route_ref=f"hal:reject:{request.arbitration.request_id}", decision_state=state),
            [HalDecisionReason("hal.reject", result.reason_code)],
        )
    return (
        "unknown",
        HalRoute(target="none", route_ref=f"hal:unknown:{request.arbitration.request_id}", decision_state="unknown"),
        [HalDecisionReason("hal.unknown", result.reason_code)],
    )


class HalRuntime:
    """Event-sourced HAL arbitration runtime."""

    def __init__(
        self,
        *,
        log: Optional[HalEventLogAdapter] = None,
        clock: Callable[[], str] | None = None,
        reducer: Optional[HalReducer] = None,
    ) -> None:
        self._log = log or HalEventLogAdapter()
        self._clock = clock or _utc_now
        self._reducer = reducer or HalReducer()
        self._state = initial_state()
        self._execution_log: list[str] = []

    @property
    def log(self) -> HalEventLogAdapter:
        return self._log

    @property
    def state(self) -> HalRuntimeState:
        return self._state

    @property
    def execution_log(self) -> list[str]:
        return list(self._execution_log)

    def now(self) -> str:
        return self._clock()

    def enter_panic(self, *, reason_code: str) -> HalEvent:
        return self._emit_and_fold(
            HAL_PANIC_ENTERED,
            request_id="hal:panic",
            payload={"reason_code": reason_code},
        )

    def enter_degraded(self, *, mode: str = "operator_only") -> HalEvent:
        return self._emit_and_fold(
            HAL_DEGRADED_MODE_ENTERED,
            request_id="hal:degraded",
            payload={"mode": mode},
        )

    def process(self, request: HalRequest) -> tuple[HalDecision, list[HalEvent]]:
        """Arbitrate request, emit events, return decision — no permits or execution."""
        emitted: list[HalEvent] = []
        now = self.now()
        idem_key = request.idempotency_key or request.arbitration.request_id
        if idem_key in self._state.processed_idempotency_keys:
            decision = self._fail_closed(
                request,
                [HalDecisionReason(DENIED_DUPLICATE, "duplicate idempotency key")],
                contradictions=request.contradictions,
            )
            emitted = list(self._emit_decision_events(decision, request))
            return decision, emitted

        emitted.append(
            self._emit_and_fold(
                HAL_REQUEST_RECEIVED,
                request_id=request.arbitration.request_id,
                payload={
                    **request.to_payload(),
                    "idempotency_key": idem_key,
                },
            )
        )

        deny_reasons = validate_hal_request(
            request,
            now=now,
            panic_active=self._state.panic.active,
            degraded_mode=self._state.degraded.mode if self._state.degraded.active else "none",
        )

        context = HalArbitrationContext(
            request_id=request.arbitration.request_id,
            proposal_ref=request.arbitration.proposal_ref,
            context_refs=request.arbitration.context_refs,
            identity_ref=request.identity_ref,
            admission_ref=request.admission_ref,
            freshness_ref=request.freshness_ref,
            contradictions=request.contradictions,
            aep_max_severity=request.arbitration.aep_max_severity,
            soar_binding=request.arbitration.soar_binding,
        )
        emitted.append(
            self._emit_and_fold(
                HAL_CONTEXT_BUILT,
                request_id=request.arbitration.request_id,
                payload=context.to_payload(),
            )
        )

        if deny_reasons:
            decision = self._fail_closed(request, deny_reasons, contradictions=request.contradictions)
            emitted.extend(self._emit_decision_events(decision, request))
            return decision, emitted

        emitted.append(
            self._emit_and_fold(
                HAL_ARBITRATION_STARTED,
                request_id=request.arbitration.request_id,
                payload={"proposal_ref": request.arbitration.proposal_ref},
            )
        )

        result = arbitrate(request.arbitration)
        decision_state, route, extra_reasons = _map_result_to_decision(
            result,
            request=request,
            contradictions=request.contradictions,
            degraded_active=self._state.degraded.active,
        )

        if route.target == "UEAK":
            emitted.append(
                self._emit_and_fold(
                    HAL_AUTHORITY_CONVERSION_CONTAINED,
                    request_id=request.arbitration.request_id,
                    payload={"attempted_target": "UEAK", "reason": DENIED_UEAK_DIRECT},
                )
            )
            decision = self._fail_closed(
                request,
                [HalDecisionReason(DENIED_UEAK_DIRECT, "HAL cannot route directly to UEAK")],
                contradictions=request.contradictions,
            )
            emitted.extend(self._emit_decision_events(decision, request))
            return decision, emitted

        decision_id = f"hal_dec_{canonical_hash(request.arbitration.request_id + now)[7:19]}"
        decision = HalDecision(
            decision_id=decision_id,
            request_id=request.arbitration.request_id,
            decision_state=decision_state,
            route=route,
            reasons=tuple(extra_reasons),
            arbitration_result=result,
            selected_candidate_ref=result.selected_candidate_ref,
            deferred_candidate_refs=result.deferred_candidate_refs,
            contradictions=request.contradictions,
        )
        emitted.extend(self._emit_decision_events(decision, request))
        return decision, emitted

    def verify_replay(self) -> tuple[bool, str]:
        from hg_hal.replay import HalReplayVerifier

        verifier = HalReplayVerifier(reducer=self._reducer)
        ok, reason, replayed = verifier.verify(self._log, expected_state=self._state)
        if ok:
            self._emit_and_fold(
                HAL_REPLAY_VERIFIED,
                request_id="hal:replay",
                payload={"state_hash": replayed.state_hash, "event_count": replayed.event_count},
            )
        return ok, reason

    def _fail_closed(
        self,
        request: HalRequest,
        reasons: list[HalDecisionReason],
        *,
        contradictions: tuple[str, ...],
    ) -> HalDecision:
        decision_id = f"hal_fc_{canonical_hash(request.arbitration.request_id)[7:15]}"
        return HalDecision(
            decision_id=decision_id,
            request_id=request.arbitration.request_id,
            decision_state="fail_closed",
            route=HalRoute(
                target="none",
                route_ref=f"hal:fail_closed:{request.arbitration.request_id}",
                decision_state="fail_closed",
            ),
            reasons=tuple(reasons),
            arbitration_result=None,
            selected_candidate_ref=None,
            deferred_candidate_refs=(),
            contradictions=contradictions,
        )

    def _emit_decision_events(self, decision: HalDecision, request: HalRequest) -> list[HalEvent]:
        events: list[HalEvent] = []
        payload = decision.to_payload()
        if decision.decision_state == "fail_closed":
            events.append(
                self._emit_and_fold(
                    HAL_FAILED_CLOSED,
                    request_id=request.arbitration.request_id,
                    payload=payload,
                )
            )
        elif decision.decision_state in {"reject", "request_clarification"}:
            events.append(
                self._emit_and_fold(
                    HAL_REJECTED,
                    request_id=request.arbitration.request_id,
                    payload=payload,
                )
            )
        else:
            events.append(
                self._emit_and_fold(
                    HAL_DECISION_PROPOSED,
                    request_id=request.arbitration.request_id,
                    payload=payload,
                )
            )

        events.append(
            self._emit_and_fold(
                HAL_ROUTE_SELECTED,
                request_id=request.arbitration.request_id,
                payload={
                    "decision_id": decision.decision_id,
                    "route": decision.route.to_payload(),
                    "contradictions": list(decision.contradictions),
                },
            )
        )

        if decision.route.target == "GPP":
            events.append(
                self._emit_and_fold(
                    HAL_GPP_ROUTE_REQUESTED,
                    request_id=request.arbitration.request_id,
                    payload={
                        "decision_id": decision.decision_id,
                        "selected_candidate_ref": decision.selected_candidate_ref,
                        "enforcement": "hal_routes_to_gpp_only_no_permit",
                    },
                )
            )
        elif decision.route.target == "operator":
            events.append(
                self._emit_and_fold(
                    HAL_OPERATOR_REVIEW_REQUESTED,
                    request_id=request.arbitration.request_id,
                    payload={"decision_id": decision.decision_id},
                )
            )

        if decision.decision_state == "route_to_UEAK":
            events.append(
                self._emit_and_fold(
                    HAL_AUTHORITY_CONVERSION_CONTAINED,
                    request_id=request.arbitration.request_id,
                    payload={"attempted": HAL_UEAK_ROUTE_REQUESTED},
                )
            )

        return events

    def _emit(self, event_type: str, *, request_id: str, payload: dict[str, Any]) -> HalEvent:
        seq = self._log.next_seq()
        return HalEvent(
            seq=seq,
            event_type=event_type,
            timestamp=self.now(),
            request_id=request_id,
            payload=payload,
        )

    def _emit_and_fold(self, event_type: str, *, request_id: str, payload: dict[str, Any]) -> HalEvent:
        event = self._emit(event_type, request_id=request_id, payload=payload)
        self._log.append(event)
        self._state = self._reducer.reduce(self._state, event)
        return event


__all__ = ["HalRuntime"]
