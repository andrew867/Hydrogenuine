"""YSR trigger, refusal, and escalation policy."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.yawn.config import YSRConfig
from hg_runtime.yawn.scratch import load_scratch, scratch_age_seconds
from hg_runtime.yawn.types import YawnDecision, YawnTriggerResult

RECOVERY_ACTIVE_STATES = frozenset(
    {
        "RECOVERY",
        "DRAINING",
        "CHECKPOINTING",
        "HYGIENE",
        "REHYDRATING",
        "SAFE_MODE",
    }
)


def _recovery_active(view: Mapping[str, Any]) -> bool:
    env = view.get("environment", {})
    if not isinstance(env, Mapping):
        return False
    return str(env.get("recovery_state", "NORMAL")) in RECOVERY_ACTIVE_STATES


def _event_lag(local_head: int, bus_head_seq: int) -> int:
    if bus_head_seq <= 0:
        return 0
    return max(0, bus_head_seq - local_head)


def evaluate_trigger(
    *,
    config: YSRConfig,
    agent_id: str,
    view: Mapping[str, Any],
    aep_state: Mapping[str, Any],
    runtime_dir: Any,
    bus_head_seq: int,
    prior_world_state_hash: str,
    refreshed_world_state_hash: str,
    panic_active: bool = False,
    operator_requested: bool = False,
) -> YawnDecision:
    if not config.enabled:
        return YawnDecision("yawn_refused", "ysr_disabled", agent_id)

    if panic_active:
        return YawnDecision("yawn_refused", "REFUSED_PANIC", agent_id)

    if _recovery_active(view):
        return YawnDecision("yawn_refused", "REFUSED_CRR_ACTIVE", agent_id)

    scratch = load_scratch(runtime_dir, agent_id)
    local_head = int(scratch.get("event_head_seq", 0) or 0)
    lag = _event_lag(local_head, bus_head_seq)
    age = scratch_age_seconds(scratch)

    if operator_requested:
        return YawnDecision("yawn_allowed", "operator_requested", agent_id)

    if lag == 0 and age == 0 and prior_world_state_hash == refreshed_world_state_hash:
        transient = scratch.get("transient", {})
        if not transient:
            return YawnDecision("no_op_already_synced", "already_synced", agent_id)

    if lag > config.max_event_lag:
        return YawnDecision("yawn_allowed", "event_head_lag", agent_id)

    if age > config.max_scratch_age_seconds:
        return YawnDecision("yawn_allowed", "scratch_age", agent_id)

    if prior_world_state_hash != refreshed_world_state_hash and lag > 0:
        return YawnDecision("yawn_allowed", "world_state_drift", agent_id)

    try:
        severity = int(aep_state.get("max_severity", 0))
    except (TypeError, ValueError):
        severity = 0
    if severity >= config.aep_suggest_severity and lag > 0:
        return YawnDecision("yawn_allowed", "aep_suggested", agent_id)

    if lag == 0 and prior_world_state_hash == refreshed_world_state_hash:
        return YawnDecision("no_op_already_synced", "already_synced", agent_id)

    return YawnDecision("yawn_refused", "no_trigger", agent_id)


def should_escalate_to_crr(
    *,
    config: YSRConfig,
    event_lag: int,
    resync_ok: bool,
) -> bool:
    if not config.escalate_to_crr_on_fail:
        return False
    if resync_ok:
        return False
    return event_lag > config.max_event_lag * 2


def map_decision_to_result(decision: YawnDecision) -> YawnTriggerResult:
    return decision.result


__all__ = [
    "RECOVERY_ACTIVE_STATES",
    "evaluate_trigger",
    "map_decision_to_result",
    "should_escalate_to_crr",
]
