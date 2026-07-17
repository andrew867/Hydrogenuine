"""SOAR event-sourced runtime — sovereign arbitration; routes fixtures only."""

from __future__ import annotations

from typing import Any, Callable, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.time.clock import get_clock

from hg_soar.collapse import build_collapse
from hg_soar.domains import evaluate_all_domains
from hg_soar.event_log import SoarEventLogAdapter
from hg_soar.events import (
    SOAR_AUTHORITY_CONVERSION_CONTAINED,
    SOAR_BUNDLE_BUILT,
    SOAR_CRITIQUE_APPLIED,
    SOAR_D7_COLLAPSE_RECORDED,
    SOAR_DECISION_RECORDED,
    SOAR_DOMAIN_SIGNAL_RECORDED,
    SOAR_FAILED_CLOSED,
    SOAR_GPP_ROUTE_FIXTURE,
    SOAR_HAL_ROUTE_REQUESTED,
    SOAR_REPLAY_VERIFIED,
    SOAR_REQUEST_RECEIVED,
    SOAR_ROUTE_SELECTED,
    SOAR_SOVEREIGN_REFUSAL,
    SOAR_UEAK_ROUTE_FIXTURE,
)
from hg_soar.models import (
    SoarArbitrationContext,
    SoarBundle,
    SoarDecision,
    SoarDecisionReason,
    SoarEvent,
    SoarRequest,
    SoarRoute,
    SoarRuntimeState,
    SovereignRefusal,
    signal_from_evaluation,
)
from hg_soar.reducer import SoarReducer
from hg_soar.replay import verify_replay
from hg_soar.state import initial_state
from hg_soar.types import D7Binding
from hg_soar.validation import validate_bundle_domains, validate_soar_request

_SOAR_ISSUER = "soar:sovereign_arbitration"


def _utc_now() -> str:
    return get_clock().now_utc()


def _proposal_event(request: SoarRequest) -> dict[str, object]:
    content = request.proposal_payload.get("content", request.proposal_payload)
    return {
        "event_id": request.proposal_ref,
        "type": "PROPOSAL_EMITTED",
        "payload": {
            "proposal_id": request.proposal_ref,
            "kind": request.proposal_payload.get("kind", "candidate_action"),
            "content": dict(content) if isinstance(content, dict) else {},
        },
    }


def _routes_for_binding(request_id: str, binding: D7Binding) -> tuple[SoarRoute, ...]:
    if binding != "ACCEPT":
        if binding in {"REJECT", "NO_OP"}:
            return (SoarRoute(target="review", route_ref=f"soar:review:{request_id}", fixture_only=True),)
        return (SoarRoute(target="none", route_ref=f"soar:defer:{request_id}", fixture_only=True),)
    return (
        SoarRoute(target="HAL", route_ref=f"soar:hal:{request_id}", fixture_only=True),
        SoarRoute(target="GPP", route_ref=f"soar:gpp:{request_id}", fixture_only=True),
        SoarRoute(target="UEAK", route_ref=f"soar:ueak:{request_id}", fixture_only=True),
    )


def _decision_state(binding: D7Binding) -> str:
    if binding == "ACCEPT":
        return "route_hal"
    if binding in {"REJECT", "NO_OP"}:
        return "sovereign_refusal"
    if binding == "DEFER":
        return "route_review"
    return "collapsed"


class SoarRuntime:
    """SOAR sovereign arbitration runtime — never mints permits or executes."""

    issuer_id: str = _SOAR_ISSUER

    def __init__(
        self,
        *,
        log: Optional[SoarEventLogAdapter] = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._log = log or SoarEventLogAdapter()
        self._clock = clock or _utc_now
        self._state = initial_state()
        self._reducer = SoarReducer()
        self._permit_mint_log: list[str] = []
        self._execution_log: list[str] = []

    @property
    def log(self) -> SoarEventLogAdapter:
        return self._log

    @property
    def state(self) -> SoarRuntimeState:
        return self._state

    @property
    def permit_mint_log(self) -> list[str]:
        return list(self._permit_mint_log)

    @property
    def execution_log(self) -> list[str]:
        return list(self._execution_log)

    def now(self) -> str:
        return self._clock()

    def _emit(self, event_type: str, request_id: str, payload: dict[str, Any]) -> SoarEvent:
        event = SoarEvent(
            seq=self._log.next_seq(),
            event_type=event_type,
            timestamp=self.now(),
            request_id=request_id,
            payload=payload,
        )
        self._log.append(event)
        self._state = self._reducer.reduce(self._state, event)
        return event

    def process(self, request: SoarRequest) -> tuple[SoarDecision, list[SoarEvent]]:
        """Evaluate domains, collapse D7, route to HAL/GPP/UEAK fixtures — no execution."""
        now = self.now()
        events: list[SoarEvent] = []

        deny_reasons = validate_soar_request(
            request,
            now=now,
            processed_keys=self._state.processed_idempotency_keys,
        )
        if deny_reasons:
            return self._fail_closed(request, deny_reasons, events)

        events.append(
            self._emit(
                SOAR_REQUEST_RECEIVED,
                request.request_id,
                {
                    "request_id": request.request_id,
                    "proposal_ref": request.proposal_ref,
                    "idempotency_key": request.idempotency_key or request.request_id,
                },
            )
        )

        proposal = _proposal_event(request)
        input_refs = (request.proposal_ref,) + request.context_refs
        evaluations = evaluate_all_domains(proposal=proposal, input_refs=input_refs)
        signals = tuple(signal_from_evaluation(e) for e in evaluations)

        context = SoarArbitrationContext(
            request_id=request.request_id,
            proposal_ref=request.proposal_ref,
            context_refs=request.context_refs,
            identity_ref=request.identity_ref,
            admission_ref=request.admission_ref,
            freshness_ref=request.freshness_ref,
            contradictions=request.contradictions,
        )
        bundle = SoarBundle(request_id=request.request_id, signals=signals, context=context)
        bundle_reasons = validate_bundle_domains(bundle)
        if bundle_reasons:
            return self._fail_closed(request, bundle_reasons, events)

        events.append(
            self._emit(
                SOAR_BUNDLE_BUILT,
                request.request_id,
                {"bundle_hash": bundle.bundle_hash, "signal_count": len(signals)},
            )
        )

        for signal in signals:
            events.append(
                self._emit(
                    SOAR_DOMAIN_SIGNAL_RECORDED,
                    request.request_id,
                    {
                        "signal_id": signal.signal_id,
                        "domain_id": signal.domain_id,
                        "advisory_only": signal.advisory_only,
                        "verdict": signal.evaluation.verdict,
                    },
                )
            )

        collapse, critique_signal, final_binding = build_collapse(
            request_id=request.request_id,
            proposal_ref=request.proposal_ref,
            signals=signals,
            extra_contradictions=request.contradictions,
        )

        events.append(
            self._emit(
                SOAR_D7_COLLAPSE_RECORDED,
                request.request_id,
                {
                    "collapse_id": collapse.collapse_id,
                    "binding": final_binding,
                    "contradictions": list(collapse.contradictions),
                    "execution_permission": False,
                },
            )
        )

        events.append(
            self._emit(
                SOAR_CRITIQUE_APPLIED,
                request.request_id,
                {
                    "critique_id": critique_signal.critique.critique_id,
                    "binding_before": critique_signal.binding_before,
                    "binding_after": critique_signal.binding_after,
                },
            )
        )

        routes = _routes_for_binding(request.request_id, final_binding)
        decision_id = f"soar_dec_{canonical_hash(request.request_id + now)[7:19]}"
        refusal: SovereignRefusal | None = None
        if final_binding in {"REJECT", "NO_OP"}:
            refusal = SovereignRefusal(
                refusal_id=f"soar_ref_{decision_id}",
                request_id=request.request_id,
                binding=final_binding,
                reasons=(SoarDecisionReason("soar.sovereign.refusal", collapse.primary_decision.reason_code),),
            )

        decision = SoarDecision(
            decision_id=decision_id,
            request_id=request.request_id,
            decision_state=_decision_state(final_binding),
            binding=final_binding,
            collapse=collapse,
            critique=critique_signal,
            routes=routes,
            reasons=(),
            refusal=refusal,
        )

        events.append(
            self._emit(
                SOAR_DECISION_RECORDED,
                request.request_id,
                {
                    "decision_id": decision.decision_id,
                    "binding": final_binding,
                    "decision_hash": decision.decision_hash,
                    "permit_minted": False,
                    "execution_approved": False,
                },
            )
        )

        events.append(
            self._emit(
                SOAR_ROUTE_SELECTED,
                request.request_id,
                {
                    "routes": [r.to_payload() for r in routes],
                    "contradictions": list(collapse.contradictions),
                },
            )
        )

        if final_binding == "ACCEPT":
            events.append(
                self._emit(
                    SOAR_HAL_ROUTE_REQUESTED,
                    request.request_id,
                    {"route_ref": routes[0].route_ref, "fixture_only": True},
                )
            )
            events.append(
                self._emit(
                    SOAR_GPP_ROUTE_FIXTURE,
                    request.request_id,
                    {"route_ref": routes[1].route_ref, "fixture_only": True, "permit_mint": False},
                )
            )
            events.append(
                self._emit(
                    SOAR_UEAK_ROUTE_FIXTURE,
                    request.request_id,
                    {"route_ref": routes[2].route_ref, "fixture_only": True, "execution_approved": False},
                )
            )
            events.append(
                self._emit(
                    SOAR_AUTHORITY_CONVERSION_CONTAINED,
                    request.request_id,
                    {"detail": "SOAR binding is advisory route only; HAL/GPP/UEAK retain authority"},
                )
            )
        elif final_binding in {"REJECT", "NO_OP"} and refusal is not None:
            events.append(
                self._emit(
                    SOAR_SOVEREIGN_REFUSAL,
                    request.request_id,
                    refusal.to_payload(),
                )
            )

        ok, reason = verify_replay(self._log, expected_state=self._state)
        events.append(
            self._emit(
                SOAR_REPLAY_VERIFIED,
                request.request_id,
                {"ok": ok, "reason": reason, "state_hash": self._state.state_hash},
            )
        )

        return decision, events

    def _fail_closed(
        self,
        request: SoarRequest,
        reasons: list[SoarDecisionReason],
        events: list[SoarEvent],
    ) -> tuple[SoarDecision, list[SoarEvent]]:
        decision_id = f"soar_fail_{canonical_hash(request.request_id)[7:19]}"
        decision = SoarDecision(
            decision_id=decision_id,
            request_id=request.request_id,
            decision_state="fail_closed",
            binding="REJECT",
            collapse=None,
            critique=None,
            routes=(SoarRoute(target="none", route_ref=f"soar:fail:{request.request_id}", fixture_only=True),),
            reasons=tuple(reasons),
            refusal=SovereignRefusal(
                refusal_id=f"soar_ref_{decision_id}",
                request_id=request.request_id,
                binding="REJECT",
                reasons=tuple(reasons),
            ),
        )
        events.append(
            self._emit(
                SOAR_FAILED_CLOSED,
                request.request_id,
                {
                    "decision_id": decision_id,
                    "binding": "REJECT",
                    "reasons": [r.to_payload() for r in reasons],
                },
            )
        )
        return decision, events


__all__ = ["SoarRuntime", "_SOAR_ISSUER"]
