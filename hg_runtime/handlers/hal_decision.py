"""RTC decision stage with HAL Phase 1 arbitration scaffold."""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

from hg_core.governance.permit_binder import PermitBinder, descriptor_for
from hg_core.governance.rtc_bridge import bind_result_to_drafts
from hg_core.governance.types import BindRequest
from hg_hal import (
    arbitrate,
    arbitration_recorded_draft,
    arbitration_requested_draft,
    decision_ref_for_result,
    hal_enabled,
    request_from_proposal,
)
from hg_runtime.contract import Event, draft, stable_id


class Phase1HALDecisionHandler:
    """HAL arbitration + GPP permit bind scaffold. HAL routes; GPP binds; neither executes."""

    handler_id = "rtc.hal.phase1_decision"

    def __init__(self, permit_binder: Optional[PermitBinder] = None) -> None:
        self._binder = permit_binder

    def evaluate(
        self,
        events: Sequence[Event],
        proposals: Sequence[Event],
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
    ) -> List[dict[str, Any]]:
        if not hal_enabled():
            from hg_runtime.handlers.decision_phase1 import Phase1DecisionHandler

            return Phase1DecisionHandler(permit_binder=self._binder).evaluate(
                events, proposals, view, aep_state
            )

        context_refs = tuple(event["event_id"] for event in events)
        modulation_refs = _aep_modulation_refs(view)
        out: List[dict[str, Any]] = []

        for proposal in proposals:
            payload = proposal.get("payload", {})
            if payload.get("kind") != "candidate_action":
                out.append(
                    draft(
                        "DECISION_BLOCKED",
                        {
                            "proposal_id": payload.get("proposal_id"),
                            "reason": "not_candidate_action",
                        },
                        causal_parents=[proposal["event_id"]],
                    )
                )
                continue

            soar_run = None
            from hg_soar import run_soar, soar_enabled, soar_run_drafts

            if soar_enabled():
                soar_run = run_soar(proposal, context_refs=context_refs)
                out.extend(
                    soar_run_drafts(soar_run, causal_parents=[proposal["event_id"]])
                )

            request = request_from_proposal(
                proposal,
                context_refs=context_refs,
                aep_state=aep_state,
                aep_modulation_refs=modulation_refs,
                soar_run=soar_run,
            )
            requested = arbitration_requested_draft(
                request, causal_parents=[proposal["event_id"]]
            )
            out.append(requested)
            result = arbitrate(request)
            recorded = arbitration_recorded_draft(
                result, causal_parents=[requested.get("event_id") or proposal["event_id"]]
            )
            out.append(recorded)

            if result.routing == "NO_OP":
                continue
            if result.routing in ("REJECT", "DEFER"):
                out.append(
                    draft(
                        "DECISION_BLOCKED",
                        {
                            "proposal_id": payload.get("proposal_id"),
                            "reason": result.reason_code,
                            "hal_arbitration_ref": result.request_id,
                            "routing": result.routing,
                        },
                        causal_parents=[proposal["event_id"]],
                    )
                )
                continue

            decision_id = stable_id("dec", proposal["event_id"])
            action = dict(payload.get("content", {}))
            action["hal_arbitration_ref"] = result.request_id
            if soar_run is not None:
                action["soar_run_ref"] = soar_run.request_id
                action["soar_binding"] = soar_run.binding
            action["governance_trace_refs"] = list(result.trace_refs)
            decision_ref = decision_ref_for_result(result)
            out.extend(
                self._gpp_drafts(
                    decision_id=decision_id,
                    proposal=proposal,
                    action=action,
                    capability_id=str(action.get("capability_id") or "cap.oea_stub_log"),
                    effect_class=str(action.get("effect_class") or "audit_log"),
                    decision_ref=decision_ref,
                    hal_arbitration_ref=result.request_id,
                )
            )
            out.append(
                draft(
                    "DECISION_EVENT",
                    {
                        "decision_id": decision_id,
                        "proposal_id": payload["proposal_id"],
                        "verdict": "allow_hal_scaffold",
                        "authority_ref": "hal-phase1-scaffold",
                        "hal_arbitration_ref": result.request_id,
                        "hal_routing": result.routing,
                        "soar_run_ref": soar_run.request_id if soar_run else None,
                        "soar_binding": soar_run.binding if soar_run else None,
                        "action": action,
                    },
                    causal_parents=[proposal["event_id"]],
                )
            )
        return out

    def _gpp_drafts(
        self,
        *,
        decision_id: str,
        proposal: Event,
        action: dict[str, Any],
        capability_id: str,
        effect_class: str,
        decision_ref: str,
        hal_arbitration_ref: str,
    ) -> List[dict[str, Any]]:
        if self._binder is None:
            return []
        bind_result = self._binder.bind(
            BindRequest(
                request_id=decision_id,
                capability_id=capability_id,
                effect_class=effect_class,
                decision_ref=decision_ref,
            ),
            descriptor_for(capability_id),
        )
        drafts = bind_result_to_drafts(bind_result)
        if bind_result.permit is not None:
            trace_ref = bind_result.permit.trace_ref
            action["permit_ref"] = bind_result.permit.permit_id
            action["governance_trace_refs"] = list(action.get("governance_trace_refs", [])) + [
                f"{trace_ref.trace_path}#{trace_ref.trace_seq}:{trace_ref.trace_event_hash}",
                f"hal:arbitration:{hal_arbitration_ref}",
            ]
        return drafts


def _aep_modulation_refs(view: Mapping[str, Any]) -> tuple[str, ...]:
    activity = view.get("activity", {})
    if not isinstance(activity, Mapping):
        return ()
    recent = activity.get("recent_aep_signals", [])
    if not isinstance(recent, list):
        return ()
    refs: list[str] = []
    for row in recent[-8:]:
        if isinstance(row, Mapping) and row.get("event_id"):
            refs.append(str(row["event_id"]))
    return tuple(refs)


__all__ = ["Phase1HALDecisionHandler"]
