"""RTC decision stage — GPP permit binder scaffold (trace/hash; no execution dispatch)."""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

from hg_core.governance.permit_binder import PermitBinder, descriptor_for
from hg_core.governance.rtc_bridge import bind_result_to_drafts
from hg_core.governance.types import BindRequest
from hg_runtime.contract import Event, draft
from hg_runtime.handlers.stubs import StubDecisionHandler


class Phase1DecisionHandler:
    """Stub decision path with optional GPP permit binding for UEAK handoff."""

    handler_id = "rtc.gpp.phase1_decision"

    def __init__(self, permit_binder: Optional[PermitBinder] = None) -> None:
        self._stub = StubDecisionHandler()
        self._binder = permit_binder

    def evaluate(
        self,
        events: Sequence[Event],
        proposals: Sequence[Event],
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
    ) -> List[dict[str, Any]]:
        base = self._stub.evaluate(events, proposals, view, aep_state)
        if self._binder is None:
            return base

        out: List[dict[str, Any]] = []
        for item in base:
            if item["type"] != "DECISION_EVENT":
                out.append(item)
                continue
            payload = dict(item.get("payload", {}))
            action = dict(payload.get("action", {}))
            capability_id = str(action.get("capability_id") or "cap.oea_stub_log")
            effect_class = str(action.get("effect_class") or "audit_log")
            bind_result = self._binder.bind(
                BindRequest(
                    request_id=str(payload.get("decision_id", "")),
                    capability_id=capability_id,
                    effect_class=effect_class,
                    decision_ref="dec_allow_stub",
                ),
                descriptor_for(capability_id),
            )
            out.extend(bind_result_to_drafts(bind_result))
            if bind_result.permit is not None:
                trace_ref = bind_result.permit.trace_ref
                action["permit_ref"] = bind_result.permit.permit_id
                action["governance_trace_refs"] = [
                    f"{trace_ref.trace_path}#{trace_ref.trace_seq}:{trace_ref.trace_event_hash}"
                ]
                payload["action"] = action
                payload["authority_ref"] = "gpp-phase1-scaffold"
                item = draft(
                    "DECISION_EVENT",
                    payload,
                    causal_parents=list(item.get("causal_parents", ())),
                )
            out.append(item)
        return out


__all__ = ["Phase1DecisionHandler"]
