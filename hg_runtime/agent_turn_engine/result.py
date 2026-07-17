"""Map broker/reasoning outcomes to agent turn verdicts."""

from __future__ import annotations

from hg_runtime.agent_zero_reasoning.schema import ReasoningFailure, ReasoningResult, ReasoningVerdict
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict, TurnReceiptVerdict
from hg_runtime.capability_broker.schema import BrokerDecision, BrokerDecisionStatus, BrokerVerdict
from hg_runtime.agent_turn_engine.schema import AgentTurnVerdict


def verdict_from_observe(observe_verdict: ObserveSnapshotVerdict) -> AgentTurnVerdict | None:
    mapping = {
        ObserveSnapshotVerdict.YELLOW_PROVIDER_UNAVAILABLE: AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE,
        ObserveSnapshotVerdict.YELLOW_LIVE_READ_UNAVAILABLE: AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_LIVE_READ_UNAVAILABLE,
        ObserveSnapshotVerdict.YELLOW_OPERATOR_ABSENT: AgentTurnVerdict.YELLOW_AGENT_TURN_OPERATOR_ABSENT,
    }
    return mapping.get(observe_verdict)


def verdict_from_receipt(chosen_action: str, receipt_verdict: TurnReceiptVerdict) -> AgentTurnVerdict:
    if receipt_verdict == TurnReceiptVerdict.YELLOW_TURN_RESTED:
        return AgentTurnVerdict.YELLOW_AGENT_TURN_RESTED
    if receipt_verdict == TurnReceiptVerdict.YELLOW_TURN_WITNESS_ONLY:
        return AgentTurnVerdict.YELLOW_AGENT_TURN_WITNESS_ONLY
    if receipt_verdict == TurnReceiptVerdict.YELLOW_PROVIDER_UNAVAILABLE:
        return AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE
    if receipt_verdict == TurnReceiptVerdict.YELLOW_LIVE_READ_UNAVAILABLE:
        return AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_LIVE_READ_UNAVAILABLE
    if chosen_action == "request_more_scope":
        return AgentTurnVerdict.YELLOW_AGENT_TURN_SCOPE_REQUESTED
    if receipt_verdict.value.startswith("RED_"):
        if receipt_verdict == TurnReceiptVerdict.RED_TURN_FIXTURE_RUNTIME:
            return AgentTurnVerdict.RED_AGENT_TURN_FIXTURE_RUNTIME
        if receipt_verdict == TurnReceiptVerdict.RED_TURN_COT_STORED:
            return AgentTurnVerdict.RED_AGENT_TURN_COT_STORED
        if receipt_verdict == TurnReceiptVerdict.RED_TURN_SECRET_STORED:
            return AgentTurnVerdict.RED_AGENT_TURN_SECRET_STORED
        if receipt_verdict == TurnReceiptVerdict.RED_TURN_EXTERNAL_SIDE_EFFECT:
            return AgentTurnVerdict.RED_AGENT_TURN_EXTERNAL_SIDE_EFFECT
        return AgentTurnVerdict.RED_AGENT_TURN_EMPTY
    return AgentTurnVerdict.GREEN_AGENT_TURN_COMPLETE_INTERNAL


def verdict_from_broker(decision: BrokerDecision) -> AgentTurnVerdict | None:
    if decision.verdict == BrokerVerdict.YELLOW_BROKER_REST:
        return AgentTurnVerdict.YELLOW_AGENT_TURN_RESTED
    if decision.verdict == BrokerVerdict.YELLOW_BROKER_WITNESS:
        return AgentTurnVerdict.YELLOW_AGENT_TURN_WITNESS_ONLY
    if decision.verdict == BrokerVerdict.YELLOW_BROKER_SCOPE_REQUEST:
        return AgentTurnVerdict.YELLOW_AGENT_TURN_SCOPE_REQUESTED
    if decision.status == BrokerDecisionStatus.DEFER:
        if BrokerVerdict.RED_BROKER_PROVIDER_UNAVAILABLE.value in str(decision.refusal_reasons):
            return AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE
        if BrokerVerdict.RED_BROKER_LIVE_READ_UNAVAILABLE.value in str(decision.refusal_reasons):
            return AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_LIVE_READ_UNAVAILABLE
    if decision.verdict.value.startswith("RED_"):
        if decision.verdict == BrokerVerdict.RED_BROKER_FIXTURE_RUNTIME:
            return AgentTurnVerdict.RED_AGENT_TURN_FIXTURE_RUNTIME
        if decision.verdict == BrokerVerdict.RED_BROKER_EXTERNAL_SIDE_EFFECT:
            return AgentTurnVerdict.RED_AGENT_TURN_EXTERNAL_SIDE_EFFECT
    return None


def reasoning_failure_allows_fallback(failure: ReasoningFailure) -> bool:
    return failure.verdict in (
        ReasoningVerdict.YELLOW_PROVIDER_UNAVAILABLE,
        ReasoningVerdict.YELLOW_REASONING_DEFERRED,
    )


def fallback_action_for_reasoning_failure(failure: ReasoningFailure, *, policy: dict) -> str:
    if failure.verdict == ReasoningVerdict.YELLOW_PROVIDER_UNAVAILABLE:
        return str(policy.get("provider_unavailable_fallback_action", "rest_turn"))
    return "witness_turn"


__all__ = [
    "fallback_action_for_reasoning_failure",
    "reasoning_failure_allows_fallback",
    "verdict_from_broker",
    "verdict_from_observe",
    "verdict_from_receipt",
]
