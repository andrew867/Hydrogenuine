"""Single-turn agent engine — one bounded turn, no loop."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_reasoning.reasoning_engine import produce_turn_intent
from hg_runtime.agent_zero_reasoning.schema import ReasoningFailure, ReasoningResult
from hg_runtime.agent_zero_state.reducer import apply_turn, reduce_state
from hg_runtime.agent_zero_state.replay import replay_agent_state, verify_replay_deterministic
from hg_runtime.agent_zero_state.turn_intent import TurnIntent, build_turn_intent
from hg_runtime.agent_zero_state.turn_receipt import TurnReceipt, build_turn_receipt, validate_turn_receipt
from hg_runtime.agent_zero_state.types import TurnIntentVerdict, TurnReceiptVerdict
from hg_runtime.capability_broker.audit_log import BrokerAuditLog
from hg_runtime.capability_broker.broker import evaluate_turn_intent
from hg_runtime.capability_broker.schema import BrokerDecisionStatus
from hg_runtime.agent_turn_engine.capability_builder import build_capability_menu_for_turn
from hg_runtime.agent_turn_engine.context_builder import (
    build_observe_snapshot_for_turn,
    load_or_initialize_agent_state,
    observe_context_summary,
    persist_observe_snapshot,
)
from hg_runtime.agent_turn_engine.errors import AgentTurnDispatchError, AgentTurnReplayError, AgentTurnValidationError
from hg_runtime.agent_turn_engine.internal_dispatch import InternalDispatchResult, dispatch_internal_action
from hg_runtime.agent_turn_engine.result import (
    fallback_action_for_reasoning_failure,
    reasoning_failure_allows_fallback,
    verdict_from_broker,
    verdict_from_observe,
    verdict_from_receipt,
)
from hg_runtime.agent_turn_engine.schema import (
    AgentTurnFailure,
    AgentTurnRequest,
    AgentTurnResult,
    AgentTurnVerdict,
    load_agent_turn_engine_policy,
    new_failure_id,
    new_result_id,
    validate_agent_turn_request,
)
from hg_runtime.agent_turn_engine.turn_storage import (
    broker_dir,
    capability_dir,
    observe_dir,
    open_journal,
    persist_turn_artifacts,
    reasoning_dir,
    turns_root,
    write_json,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _provider_status(observe) -> str:
    return "available" if observe.provider_reality_refs else "unavailable"


def _live_read_status(observe) -> str:
    return "available" if observe.live_read_receipt_refs else "unavailable"


def _failure(
    request: AgentTurnRequest,
    *,
    stage: str,
    reason: str,
    verdict: AgentTurnVerdict,
    partial_refs: dict[str, str] | None = None,
) -> AgentTurnFailure:
    return AgentTurnFailure(
        failure_id=new_failure_id(),
        request_id=request.request_id,
        failure_stage=stage,
        reason=reason,
        partial_refs=dict(partial_refs or {}),
        verdict=verdict,
        created_at=_now_iso(),
    ).with_hash()


def _build_fallback_intent(
    *,
    request: AgentTurnRequest,
    agent_state,
    menu,
    observe,
    turn_index: int,
    failure: ReasoningFailure,
    policy: dict[str, Any],
) -> TurnIntent:
    action = fallback_action_for_reasoning_failure(failure, policy=policy)
    summary = observe_context_summary(observe.snapshot_verdict, observe)
    iv, intent = build_turn_intent(
        agent_id=agent_state.agent_id,
        turn_index=turn_index,
        chosen_action=action,
        menu=menu,
        observation_summary=summary,
        why_this_action=f"reasoning unavailable: {failure.reason}",
        run_id=request.run_id,
        provider_receipt_ref=failure.provider_receipt_ref,
    )
    if iv != TurnIntentVerdict.GREEN_TURN_INTENT_VALID:
        raise AgentTurnValidationError(iv.value)
    return intent


def run_single_agent_turn(
    request: AgentTurnRequest,
    *,
    provider_invoke=None,
    base: Path | None = None,
) -> AgentTurnResult | AgentTurnFailure:
    """Run exactly one bounded agent turn — no loop, no external side effects."""
    policy = load_agent_turn_engine_policy()
    if not policy.get("single_turn_only", True):
        return _failure(request, stage="policy", reason="single_turn_only false", verdict=AgentTurnVerdict.RED_AGENT_TURN_EMPTY)

    try:
        request = validate_agent_turn_request(request)
    except AgentTurnValidationError as exc:
        return _failure(request, stage="validate_request", reason=str(exc), verdict=AgentTurnVerdict.RED_AGENT_TURN_EMPTY)

    storage_base = base or turns_root()
    started_at = _now_iso()

    try:
        agent_state = load_or_initialize_agent_state(request, base=storage_base)
    except AgentTurnValidationError as exc:
        return _failure(request, stage="load_state", reason=str(exc), verdict=AgentTurnVerdict.RED_AGENT_TURN_FIXTURE_RUNTIME)

    initial_state = agent_state
    turn_index = agent_state.turn_index + 1
    prev_hash = agent_state.last_turn_hash

    try:
        observe_verdict, observe = build_observe_snapshot_for_turn(
            request=request,
            agent_state=agent_state,
            turn_index=turn_index,
        )
    except AgentTurnValidationError as exc:
        return _failure(request, stage="observe", reason=str(exc), verdict=AgentTurnVerdict.RED_AGENT_TURN_EMPTY)

    menu = build_capability_menu_for_turn(
        agent_state=agent_state,
        observe_snapshot=observe,
        operator_presence=request.operator_presence,
        provider_status=_provider_status(observe),
        live_read_status=_live_read_status(observe),
    )

    artifact_paths: dict[str, Path] = {}
    obs_path = observe_dir(request.run_id, base=storage_base) / f"{observe.snapshot_id}.json"
    menu_path = capability_dir(request.run_id, base=storage_base) / f"{menu.menu_id}.json"
    persist_observe_snapshot(observe, obs_path)
    write_json(menu_path, menu.to_payload())
    artifact_paths["observe"] = obs_path
    artifact_paths["menu"] = menu_path

    reasoning_result: ReasoningResult | None = None
    reasoning_failure: ReasoningFailure | None = None
    reasoning_out = produce_turn_intent(
        agent_state=agent_state,
        observe_snapshot=observe,
        capability_menu=menu,
        provider_invoke=provider_invoke if request.allow_provider else None,
        store_receipt=True,
    )

    if isinstance(reasoning_out, ReasoningFailure):
        reasoning_failure = reasoning_out
        reasoning_path = reasoning_dir(request.run_id, base=storage_base) / f"{reasoning_failure.failure_id}.json"
        write_json(reasoning_path, reasoning_failure.to_payload())
        artifact_paths["reasoning"] = reasoning_path

        if not reasoning_failure_allows_fallback(reasoning_failure):
            verdict = AgentTurnVerdict.RED_AGENT_TURN_EMPTY
            if reasoning_failure.verdict.value.startswith("RED_"):
                if "COT" in reasoning_failure.verdict.value:
                    verdict = AgentTurnVerdict.RED_AGENT_TURN_COT_STORED
                elif "SECRET" in reasoning_failure.verdict.value:
                    verdict = AgentTurnVerdict.RED_AGENT_TURN_SECRET_STORED
            return _failure(
                request,
                stage="reasoning",
                reason=reasoning_failure.reason,
                verdict=verdict,
                partial_refs={"observe_snapshot_ref": observe.snapshot_id},
            )

        if policy.get("provider_fallback_allowed_as_cognition"):
            return _failure(
                request,
                stage="reasoning",
                reason="provider fallback as cognition forbidden",
                verdict=AgentTurnVerdict.RED_AGENT_TURN_EMPTY,
            )

        turn_intent = _build_fallback_intent(
            request=request,
            agent_state=agent_state,
            menu=menu,
            observe=observe,
            turn_index=turn_index,
            failure=reasoning_failure,
            policy=policy,
        )
    else:
        reasoning_result = reasoning_out
        reasoning_path = reasoning_dir(request.run_id, base=storage_base) / f"{reasoning_result.result_id}.json"
        write_json(reasoning_path, reasoning_result.to_payload())
        artifact_paths["reasoning"] = reasoning_path
        turn_intent = reasoning_result.turn_intent

    if not policy.get("broker_required", True):
        return _failure(request, stage="broker", reason="broker bypass forbidden", verdict=AgentTurnVerdict.RED_AGENT_TURN_BROKER_BYPASS)

    audit = BrokerAuditLog(broker_dir(request.run_id, base=storage_base) / "broker_audit.jsonl")
    decision = evaluate_turn_intent(
        turn_intent=turn_intent,
        agent_state=agent_state,
        observe_snapshot=observe,
        capability_menu=menu,
        audit_log=audit,
    )
    broker_path = broker_dir(request.run_id, base=storage_base) / f"{decision.decision_id}.json"
    write_json(broker_path, decision.to_payload())
    artifact_paths["broker"] = broker_path

    dispatch_result: InternalDispatchResult | None = None
    chosen_action = turn_intent.chosen_action
    action_status = "completed"

    if decision.refused or decision.deferred:
        action_status = "deferred" if decision.deferred else "refused"
        if not decision.admitted:
            chosen_action = turn_intent.chosen_action
    elif request.allow_internal_dispatch and decision.admitted:
        try:
            dispatch_result = dispatch_internal_action(
                run_id=request.run_id,
                turn_index=turn_index,
                decision=decision,
                turn_intent=turn_intent,
                observe_snapshot_ref=observe.snapshot_id,
                live_read_receipt_refs=list(observe.live_read_receipt_refs),
                capability_menu_ref=menu.menu_id,
                reasoning_receipt_ref=reasoning_result.result_id if reasoning_result else None,
                base=storage_base,
            )
            artifact_paths["dispatch"] = Path(dispatch_result.artifact_ref) if dispatch_result.artifact_ref else None
        except AgentTurnDispatchError as exc:
            return _failure(
                request,
                stage="dispatch",
                reason=str(exc),
                verdict=AgentTurnVerdict.RED_AGENT_TURN_EXTERNAL_SIDE_EFFECT,
                partial_refs={"broker_decision_ref": decision.decision_id},
            )

    witness_ref = dispatch_result.witness_receipt_ref if dispatch_result else None
    scope_refs = list(dispatch_result.scope_request_refs if dispatch_result else turn_intent.scope_requests)
    operator_refs = list(dispatch_result.operator_question_refs if dispatch_result else turn_intent.operator_questions)

    if reasoning_failure and reasoning_failure.verdict.value == "YELLOW_PROVIDER_UNAVAILABLE":
        receipt_verdict = TurnReceiptVerdict.YELLOW_PROVIDER_UNAVAILABLE
    elif observe_verdict.value == "YELLOW_LIVE_READ_UNAVAILABLE":
        receipt_verdict = TurnReceiptVerdict.YELLOW_LIVE_READ_UNAVAILABLE
    else:
        receipt_verdict = None

    _, receipt = build_turn_receipt(
        agent_id=agent_state.agent_id,
        turn_index=turn_index,
        runtime_mode=request.runtime_mode,
        observe_snapshot_ref=observe.snapshot_id,
        capability_menu_ref=menu.menu_id,
        chosen_action=chosen_action,
        action_status=action_status,
        provider_receipt_refs=list(observe.provider_reality_refs),
        live_read_receipt_refs=list(observe.live_read_receipt_refs),
        turn_intent_ref=turn_intent.intent_id,
        witness_receipt_ref=witness_ref,
        scope_request_refs=scope_refs,
        operator_question_refs=operator_refs,
        run_id=request.run_id,
        previous_turn_hash=prev_hash,
        turn_started_at=started_at,
        turn_finished_at=_now_iso(),
    )

    receipt = TurnReceipt(
        **{
            **receipt.__dict__,
            "broker_decision_ref": decision.decision_id,
            "action_result_ref": dispatch_result.output_artifact_ref or dispatch_result.dispatch_result_id if dispatch_result else None,
            "output_quality_ref": dispatch_result.quality_receipt_ref if dispatch_result else None,
        }
    ).with_hash()

    if receipt_verdict:
        receipt = TurnReceipt(**{**receipt.__dict__, "verdict": receipt_verdict}).with_hash()

    rv, receipt = validate_turn_receipt(receipt)
    if rv.value.startswith("RED_"):
        return _failure(request, stage="receipt", reason=rv.value, verdict=AgentTurnVerdict.RED_AGENT_TURN_NO_RECEIPT)

    journal = open_journal(request.run_id, base=storage_base)
    next_state = reduce_state(agent_state, receipt)
    journal.append(receipt)
    journal.verify_chain()

    if policy.get("replay_verification_required", True):
        if not verify_replay_deterministic(initial_state, journal, next_state):
            return _failure(request, stage="replay", reason="replay hash mismatch", verdict=AgentTurnVerdict.RED_AGENT_TURN_REPLAY_FAILED)

    storage_refs = persist_turn_artifacts(
        run_id=request.run_id,
        state=next_state,
        receipt=receipt,
        journal=journal,
        artifact_paths={k: v for k, v in artifact_paths.items() if v is not None},
        base=storage_base,
        skip_journal_append=True,
    )

    turn_verdict = verdict_from_receipt(chosen_action, receipt.verdict)
    broker_verdict = verdict_from_broker(decision)
    if broker_verdict:
        turn_verdict = broker_verdict
    observe_mapped = verdict_from_observe(observe_verdict)
    if observe_mapped and turn_verdict == AgentTurnVerdict.GREEN_AGENT_TURN_COMPLETE_INTERNAL:
        turn_verdict = observe_mapped
    if reasoning_failure and reasoning_failure_allows_fallback(reasoning_failure):
        if turn_verdict == AgentTurnVerdict.GREEN_AGENT_TURN_COMPLETE_INTERNAL:
            turn_verdict = AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE
    if decision.status == BrokerDecisionStatus.REQUEST_SCOPE:
        turn_verdict = AgentTurnVerdict.YELLOW_AGENT_TURN_SCOPE_REQUESTED

    return AgentTurnResult(
        result_id=new_result_id(),
        request_id=request.request_id,
        agent_id=agent_state.agent_id,
        run_id=request.run_id,
        turn_index=turn_index,
        agent_state_ref=agent_state.state_hash or f"state-{agent_state.agent_id}",
        observe_snapshot_ref=observe.snapshot_id,
        capability_menu_ref=menu.menu_id,
        reasoning_result_ref=reasoning_result.result_id if reasoning_result else None,
        reasoning_failure_ref=reasoning_failure.failure_id if reasoning_failure else None,
        broker_decision_ref=decision.decision_id,
        dispatch_result_ref=dispatch_result.dispatch_result_id if dispatch_result else None,
        turn_receipt_ref=receipt.receipt_id,
        journal_ref=str(journal.path),
        state_after_ref=next_state.state_hash or "",
        verdict=turn_verdict,
        storage_refs=storage_refs,
        created_at=_now_iso(),
    ).with_hash()


__all__ = ["run_single_agent_turn"]
