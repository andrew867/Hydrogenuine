"""Capability broker — dispose TurnIntent without execution."""

from __future__ import annotations

from typing import Any

from hg_runtime.agent_zero_state.capability_menu import CapabilityMenuSnapshot
from hg_runtime.agent_zero_state.observe_snapshot import ObserveSnapshot
from hg_runtime.agent_zero_state.redaction import scan_payload
from hg_runtime.agent_zero_state.state import AgentState
from hg_runtime.agent_zero_state.turn_intent import TurnIntent
from hg_runtime.capability_broker.action_registry import get_action, is_forbidden_action, is_known_action
from hg_runtime.capability_broker.dispatch_plan import create_dispatch_plan
from hg_runtime.capability_broker.policy import load_capability_broker_policy
from hg_runtime.capability_broker.refusals import (
    RESTRICTIVE_OPERATOR_STATES,
    refusal_verdict,
    status_for_action,
    verdict_for_admitted_action,
)
from hg_runtime.capability_broker.schema import (
    BrokerDecision,
    BrokerDecisionStatus,
    BrokerRefusalReason,
    BrokerRequest,
    BrokerVerdict,
    CapabilityPolicy,
    new_decision_id,
    new_request_id,
    validate_broker_decision,
)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _menu_action(menu: CapabilityMenuSnapshot, action_id: str):
    return next((a for a in menu.actions if a.action_id == action_id), None)


def _stop_or_panic_active(stop_panic_state: dict[str, Any]) -> bool:
    return bool(
        stop_panic_state.get("stop_requested")
        or stop_panic_state.get("panic_requested")
        or stop_panic_state.get("panic_active")
        or stop_panic_state.get("stop_active")
    )


def _build_request(
    *,
    turn_intent: TurnIntent,
    agent_state: AgentState,
    observe_snapshot: ObserveSnapshot,
    capability_menu: CapabilityMenuSnapshot,
) -> BrokerRequest:
    return BrokerRequest(
        request_id=new_request_id(),
        agent_id=turn_intent.agent_id,
        run_id=turn_intent.run_id or agent_state.run_id,
        turn_index=turn_intent.turn_index,
        turn_intent_ref=turn_intent.intent_id,
        turn_intent=turn_intent,
        agent_state_ref=agent_state.state_hash or f"state-{agent_state.agent_id}",
        agent_state=agent_state,
        observe_snapshot_ref=observe_snapshot.snapshot_id,
        observe_snapshot=observe_snapshot,
        capability_menu_ref=capability_menu.menu_id,
        capability_menu=capability_menu,
        runtime_mode=agent_state.runtime_mode,
        operator_presence=observe_snapshot.operator_presence,
        provider_receipt_refs=list(observe_snapshot.provider_reality_refs),
        live_read_receipt_refs=list(observe_snapshot.live_read_receipt_refs),
        witness_receipt_refs=[observe_snapshot.witness_state_ref] if observe_snapshot.witness_state_ref else [],
        failure_posture_refs=list(observe_snapshot.failure_posture_refs),
        scope_request_refs=list(turn_intent.scope_requests),
        stop_panic_state=dict(agent_state.stop_panic_state),
        created_at=_now_iso(),
    ).with_hash()


def _refuse_decision(
    request: BrokerRequest,
    *,
    action_id: str,
    reason: BrokerRefusalReason,
    status: BrokerDecisionStatus = BrokerDecisionStatus.REFUSE,
    deferred: bool = False,
    policy: CapabilityPolicy,
) -> BrokerDecision:
    severe = reason in (
        BrokerRefusalReason.UNKNOWN_ACTION,
        BrokerRefusalReason.FORBIDDEN_ACTION,
        BrokerRefusalReason.EXTERNAL_SIDE_EFFECT,
        BrokerRefusalReason.FIXTURE_RUNTIME,
        BrokerRefusalReason.STOP_PANIC_BLOCK,
        BrokerRefusalReason.SECRET_LEAK,
        BrokerRefusalReason.COT_LEAK,
    )
    if reason == BrokerRefusalReason.DISABLED_ACTION:
        severe = True
    verdict = refusal_verdict(reason, severe=severe)
    if deferred:
        status = BrokerDecisionStatus.DEFER
        if verdict.value.startswith("RED_BROKER_PROVIDER") or verdict.value.startswith("RED_BROKER_LIVE"):
            verdict = BrokerVerdict.YELLOW_BROKER_DEFERRED

    decision = BrokerDecision(
        decision_id=new_decision_id(),
        request_id=request.request_id,
        agent_id=request.agent_id,
        run_id=request.run_id,
        turn_index=request.turn_index,
        chosen_action=action_id,
        status=status,
        admitted=False,
        refused=not deferred,
        deferred=deferred,
        internal_only=True,
        external_side_effect=False,
        refusal_reasons=[reason.value],
        requirements_checked={"reason": reason.value},
        policy_refs=list(policy.policy_refs),
        created_at=request.created_at,
        verdict=verdict,
    ).with_hash()
    return decision


def _admit_decision(
    request: BrokerRequest,
    *,
    action_id: str,
    policy: CapabilityPolicy,
    required_receipts: list[str] | None = None,
    operator_question_refs: list[str] | None = None,
    scope_request_refs: list[str] | None = None,
    witness_receipt_ref: str | None = None,
) -> tuple[BrokerDecision, str | None]:
    status = status_for_action(action_id)
    verdict = verdict_for_admitted_action(action_id)
    admitted = status in (
        BrokerDecisionStatus.ADMIT_INTERNAL,
        BrokerDecisionStatus.REST,
        BrokerDecisionStatus.WITNESS,
    )

    decision_id = new_decision_id()
    dispatch_ref = None
    if admitted and action_id not in (
        "rest_turn",
        "witness_turn",
        "request_more_scope",
        "propose_operator_question",
    ):
        plan = create_dispatch_plan(
            decision_id=decision_id,
            action_id=action_id,
            required_receipts=required_receipts or [],
        )
        dispatch_ref = plan.dispatch_plan_id

    decision = BrokerDecision(
        decision_id=decision_id,
        request_id=request.request_id,
        agent_id=request.agent_id,
        run_id=request.run_id,
        turn_index=request.turn_index,
        chosen_action=action_id,
        status=status,
        admitted=admitted or status in (BrokerDecisionStatus.REQUEST_SCOPE, BrokerDecisionStatus.REQUEST_OPERATOR),
        refused=False,
        deferred=False,
        internal_only=True,
        external_side_effect=False,
        dispatch_plan_ref=dispatch_ref,
        refusal_reasons=[],
        operator_question_refs=list(operator_question_refs or []),
        scope_request_refs=list(scope_request_refs or []),
        witness_receipt_ref=witness_receipt_ref,
        requirements_checked={
            "operator": request.operator_presence,
            "provider_refs": len(request.provider_receipt_refs),
            "live_read_refs": len(request.live_read_receipt_refs),
        },
        policy_refs=list(policy.policy_refs),
        created_at=request.created_at,
        verdict=verdict,
    ).with_hash()
    return decision, dispatch_ref


def evaluate_turn_intent(
    *,
    turn_intent: TurnIntent,
    agent_state: AgentState,
    observe_snapshot: ObserveSnapshot,
    capability_menu: CapabilityMenuSnapshot,
    policy: CapabilityPolicy | None = None,
    audit_log=None,
) -> BrokerDecision:
    """Evaluate TurnIntent and produce BrokerDecision — no execution."""
    policy = policy or load_capability_broker_policy()
    action_id = turn_intent.chosen_action

    intent_payload = turn_intent.to_payload()
    has_secret, has_cot = scan_payload(intent_payload)
    if has_secret and not policy.secret_storage_allowed:
        request = _build_request(
            turn_intent=turn_intent,
            agent_state=agent_state,
            observe_snapshot=observe_snapshot,
            capability_menu=capability_menu,
        )
        return _refuse_decision(
            request, action_id=action_id, reason=BrokerRefusalReason.SECRET_LEAK, policy=policy
        )
    if has_cot and not policy.hidden_chain_of_thought_storage_allowed:
        request = _build_request(
            turn_intent=turn_intent,
            agent_state=agent_state,
            observe_snapshot=observe_snapshot,
            capability_menu=capability_menu,
        )
        return _refuse_decision(
            request, action_id=action_id, reason=BrokerRefusalReason.COT_LEAK, policy=policy
        )

    request = _build_request(
        turn_intent=turn_intent,
        agent_state=agent_state,
        observe_snapshot=observe_snapshot,
        capability_menu=capability_menu,
    )

    if _stop_or_panic_active(request.stop_panic_state) and policy.stop_panic_blocks_all_non_emergency_actions:
        if action_id not in ("rest_turn", "witness_turn"):
            return _refuse_decision(
                request,
                action_id=action_id,
                reason=BrokerRefusalReason.STOP_PANIC_BLOCK,
                status=BrokerDecisionStatus.PANIC_REQUIRED,
                policy=policy,
            )

    if is_forbidden_action(action_id):
        return _refuse_decision(
            request, action_id=action_id, reason=BrokerRefusalReason.FORBIDDEN_ACTION, policy=policy
        )

    if not is_known_action(action_id):
        return _refuse_decision(
            request, action_id=action_id, reason=BrokerRefusalReason.UNKNOWN_ACTION, policy=policy
        )

    registry_action = get_action(action_id)
    menu_action = _menu_action(capability_menu, action_id)
    if menu_action is None:
        return _refuse_decision(
            request, action_id=action_id, reason=BrokerRefusalReason.UNKNOWN_ACTION, policy=policy
        )

    if not menu_action.enabled and not policy.disabled_actions_allowed:
        return _refuse_decision(
            request, action_id=action_id, reason=BrokerRefusalReason.DISABLED_ACTION, policy=policy
        )

    if registry_action and registry_action.external_side_effect and not policy.external_side_effects_allowed:
        return _refuse_decision(
            request, action_id=action_id, reason=BrokerRefusalReason.EXTERNAL_SIDE_EFFECT, policy=policy
        )

    if agent_state.runtime_mode == "fixture" and not policy.fixture_runtime_truth_allowed:
        return _refuse_decision(
            request, action_id=action_id, reason=BrokerRefusalReason.FIXTURE_RUNTIME, policy=policy
        )

    restrictive = request.operator_presence in RESTRICTIVE_OPERATOR_STATES
    if restrictive and not policy.operator_absence_expands_authority:
        if registry_action and registry_action.requires_operator:
            return _refuse_decision(
                request, action_id=action_id, reason=BrokerRefusalReason.OPERATOR_ABSENT, policy=policy
            )
        if not registry_action.internal_only:
            return _refuse_decision(
                request, action_id=action_id, reason=BrokerRefusalReason.OPERATOR_ABSENT, policy=policy
            )

    provider_ok = bool(request.provider_receipt_refs)
    if registry_action and registry_action.requires_provider and not provider_ok:
        if policy.provider_unavailable_blocks_provider_required_actions:
            return _refuse_decision(
                request,
                action_id=action_id,
                reason=BrokerRefusalReason.PROVIDER_UNAVAILABLE,
                deferred=True,
                policy=policy,
            )

    live_ok = bool(request.live_read_receipt_refs)
    if registry_action and registry_action.requires_live_read and not live_ok:
        if policy.live_read_unavailable_blocks_read_required_actions:
            return _refuse_decision(
                request,
                action_id=action_id,
                reason=BrokerRefusalReason.LIVE_READ_UNAVAILABLE,
                deferred=True,
                policy=policy,
            )

    required = []
    if provider_ok:
        required.extend(request.provider_receipt_refs)
    if live_ok:
        required.extend(request.live_read_receipt_refs)

    witness_ref = request.witness_receipt_refs[0] if request.witness_receipt_refs else None
    decision, _ = _admit_decision(
        request,
        action_id=action_id,
        policy=policy,
        required_receipts=required,
        operator_question_refs=turn_intent.operator_questions,
        scope_request_refs=turn_intent.scope_requests,
        witness_receipt_ref=witness_ref if action_id == "witness_turn" else None,
    )

    val = validate_broker_decision(decision)
    if val.value.startswith("RED_"):
        decision = BrokerDecision(**{**decision.__dict__, "verdict": val, "refused": True, "admitted": False})

    if audit_log is not None:
        from hg_runtime.capability_broker.audit_log import append_decision_to_audit
        append_decision_to_audit(audit_log, decision, request_id=request.request_id)

    return decision


__all__ = ["evaluate_turn_intent"]
