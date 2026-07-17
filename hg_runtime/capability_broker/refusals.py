"""Broker refusal helpers."""

from __future__ import annotations

from hg_runtime.capability_broker.schema import (
    BrokerDecisionStatus,
    BrokerRefusalReason,
    BrokerVerdict,
)

RESTRICTIVE_OPERATOR_STATES = frozenset({
    "operator_absent",
    "operator_unknown",
    "operator_stale",
})


def refusal_verdict(reason: BrokerRefusalReason, *, severe: bool = False) -> BrokerVerdict:
    mapping = {
        BrokerRefusalReason.UNKNOWN_ACTION: BrokerVerdict.RED_BROKER_UNKNOWN_ACTION,
        BrokerRefusalReason.DISABLED_ACTION: BrokerVerdict.RED_BROKER_DISABLED_ACTION,
        BrokerRefusalReason.EXTERNAL_SIDE_EFFECT: BrokerVerdict.RED_BROKER_EXTERNAL_SIDE_EFFECT,
        BrokerRefusalReason.OPERATOR_ABSENT: BrokerVerdict.RED_BROKER_OPERATOR_ABSENT,
        BrokerRefusalReason.PROVIDER_UNAVAILABLE: BrokerVerdict.RED_BROKER_PROVIDER_UNAVAILABLE,
        BrokerRefusalReason.LIVE_READ_UNAVAILABLE: BrokerVerdict.RED_BROKER_LIVE_READ_UNAVAILABLE,
        BrokerRefusalReason.FIXTURE_RUNTIME: BrokerVerdict.RED_BROKER_FIXTURE_RUNTIME,
        BrokerRefusalReason.STOP_PANIC_BLOCK: BrokerVerdict.RED_BROKER_STOP_PANIC_BLOCK,
        BrokerRefusalReason.FORBIDDEN_ACTION: BrokerVerdict.RED_BROKER_EXTERNAL_SIDE_EFFECT,
        BrokerRefusalReason.SECRET_LEAK: BrokerVerdict.RED_BROKER_SECRET_LEAK,
        BrokerRefusalReason.COT_LEAK: BrokerVerdict.RED_BROKER_COT_LEAK,
    }
    verdict = mapping.get(reason, BrokerVerdict.YELLOW_BROKER_REFUSED)
    if not severe and reason in (
        BrokerRefusalReason.PROVIDER_UNAVAILABLE,
        BrokerRefusalReason.LIVE_READ_UNAVAILABLE,
    ):
        return BrokerVerdict.YELLOW_BROKER_DEFERRED
    return verdict


def status_for_action(action_id: str) -> BrokerDecisionStatus:
    if action_id == "rest_turn":
        return BrokerDecisionStatus.REST
    if action_id == "witness_turn":
        return BrokerDecisionStatus.WITNESS
    if action_id == "request_more_scope":
        return BrokerDecisionStatus.REQUEST_SCOPE
    if action_id == "propose_operator_question":
        return BrokerDecisionStatus.REQUEST_OPERATOR
    return BrokerDecisionStatus.ADMIT_INTERNAL


def verdict_for_admitted_action(action_id: str) -> BrokerVerdict:
    if action_id == "rest_turn":
        return BrokerVerdict.YELLOW_BROKER_REST
    if action_id == "witness_turn":
        return BrokerVerdict.YELLOW_BROKER_WITNESS
    if action_id == "request_more_scope":
        return BrokerVerdict.YELLOW_BROKER_SCOPE_REQUEST
    if action_id == "propose_operator_question":
        return BrokerVerdict.YELLOW_BROKER_OPERATOR_QUESTION
    return BrokerVerdict.GREEN_BROKER_ADMITTED_INTERNAL


__all__ = [
    "RESTRICTIVE_OPERATOR_STATES",
    "refusal_verdict",
    "status_for_action",
    "verdict_for_admitted_action",
]
