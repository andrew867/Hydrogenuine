"""UEAK commit scaffold — permission gate before OEA handoff."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from hg_core.governance.capability_registry import lookup_capability
from hg_runtime.contract import Event, draft, stable_id
from hg_ueak.policy import effect_requires_permit, resolve_capability_for_action
from hg_ueak.types import ExecutionRequest, ExecutionResult


class CommitScaffold:
    """Phase 1 UEAK boundary: bind permit policy, emit commit/deny drafts only."""

    handler_id = "ueak.phase1.commit_scaffold"

    def __init__(self) -> None:
        self.blocked = False
        self.committed_requests: List[Dict[str, Any]] = []
        self.denied_requests: List[Dict[str, Any]] = []

    def execute(
        self, decisions: Sequence[Event], view: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        del view
        results: List[Dict[str, Any]] = []
        for decision in decisions:
            if decision["type"] != "DECISION_EVENT":
                continue
            request = request_from_decision(decision)
            if self.blocked:
                result = ExecutionResult(
                    status="DENIED",
                    reason_code="panic_blocked",
                    request_id=request.request_id,
                    capability_id=request.required_capability,
                    effect_class=request.effect_class,
                )
                self.denied_requests.append(result.to_payload())
                results.append(deny_draft(request, result, decision["event_id"]))
                continue
            result = self.evaluate(request)
            if result.status == "COMMITTED":
                self.committed_requests.append(request.to_payload())
                results.append(commit_draft(request, result, decision["event_id"]))
            else:
                self.denied_requests.append(result.to_payload())
                results.append(deny_draft(request, result, decision["event_id"]))
        return results

    def evaluate(self, request: ExecutionRequest) -> ExecutionResult:
        capability = lookup_capability(request.required_capability)
        if capability is None:
            return ExecutionResult(
                status="DENIED",
                reason_code="unknown_capability",
                request_id=request.request_id,
                capability_id=request.required_capability,
                effect_class=request.effect_class,
            )
        if capability.effect_class != request.effect_class:
            return ExecutionResult(
                status="DENIED",
                reason_code="effect_class_mismatch",
                request_id=request.request_id,
                capability_id=request.required_capability,
                effect_class=request.effect_class,
            )
        if not capability.bind_allowed:
            return ExecutionResult(
                status="DENIED",
                reason_code="capability_denied",
                request_id=request.request_id,
                capability_id=request.required_capability,
                effect_class=request.effect_class,
            )
        if effect_requires_permit(request.effect_class) and not request.permit_ref:
            return ExecutionResult(
                status="DENIED",
                reason_code="missing_permit",
                request_id=request.request_id,
                capability_id=request.required_capability,
                effect_class=request.effect_class,
            )
        commit_ref = stable_id("ueak_commit", request.request_id)
        return ExecutionResult(
            status="COMMITTED",
            reason_code="committed_internal",
            request_id=request.request_id,
            commit_ref=commit_ref,
            capability_id=request.required_capability,
            effect_class=request.effect_class,
        )

    def block_all(self) -> None:
        self.blocked = True

    def unblock(self) -> None:
        self.blocked = False


def request_from_decision(decision: Event) -> ExecutionRequest:
    payload = decision.get("payload", {})
    action = dict(payload.get("action", {}))
    capability_id, effect_class = resolve_capability_for_action(action)
    trace_refs = action.get("governance_trace_refs", ())
    if isinstance(trace_refs, str):
        trace_refs = (trace_refs,)
    return ExecutionRequest(
        request_id=stable_id("exec_req", decision["event_id"]),
        proposed_action=action,
        required_capability=capability_id,
        effect_class=effect_class,
        governance_trace_refs=tuple(str(ref) for ref in trace_refs),
        permit_ref=action.get("permit_ref"),
        decision_id=str(payload.get("decision_id", "")),
        decision_event_id=str(decision["event_id"]),
    )


def commit_draft(
    request: ExecutionRequest,
    result: ExecutionResult,
    decision_event_id: str,
) -> Dict[str, Any]:
    return draft(
        "UEAK_EXECUTION_COMMITTED",
        {
            "request_id": request.request_id,
            "commit_ref": result.commit_ref,
            "decision_id": request.decision_id,
            "decision_event_id": decision_event_id,
            "capability_id": request.required_capability,
            "effect_class": request.effect_class,
            "permit_ref": request.permit_ref,
            "governance_trace_refs": list(request.governance_trace_refs),
            "action": dict(request.proposed_action),
            "reason_code": result.reason_code,
        },
        causal_parents=[decision_event_id],
    )


def deny_draft(
    request: ExecutionRequest,
    result: ExecutionResult,
    decision_event_id: str,
) -> Dict[str, Any]:
    return draft(
        "UEAK_EXECUTION_DENIED",
        {
            "request_id": request.request_id,
            "decision_id": request.decision_id,
            "decision_event_id": decision_event_id,
            "capability_id": request.required_capability,
            "effect_class": request.effect_class,
            "permit_ref": request.permit_ref,
            "reason_code": result.reason_code,
        },
        causal_parents=[decision_event_id],
    )


__all__ = [
    "CommitScaffold",
    "commit_draft",
    "deny_draft",
    "request_from_decision",
]
