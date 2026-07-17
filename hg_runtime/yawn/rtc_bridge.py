"""YSR RTC event drafts — observation only, no bus bypass."""

from __future__ import annotations

from typing import Any

from hg_runtime.contract import draft
from hg_runtime.yawn.types import ResyncResult, ScratchSnapshot, YawnCycle


def yawn_requested(cycle: YawnCycle, *, reason: str) -> dict[str, Any]:
    return draft(
        "YSR_YAWN_REQUESTED",
        {
            "cycle": cycle.to_payload(),
            "reason_code": reason,
            "observation_only": True,
        },
    )


def yawn_started(cycle: YawnCycle) -> dict[str, Any]:
    return draft(
        "YSR_YAWN_STARTED",
        {
            "cycle_id": cycle.cycle_id,
            "agent_id": cycle.agent_id,
            "requested_at": cycle.requested_at,
            "observation_only": True,
        },
    )


def scratch_snapshot_recorded(snapshot: ScratchSnapshot, *, cycle_id: str) -> dict[str, Any]:
    return draft(
        "YSR_SCRATCH_SNAPSHOT_RECORDED",
        {
            **snapshot.to_payload(),
            "cycle_id": cycle_id,
            "observation_only": True,
        },
    )


def scratch_cleared(
    *,
    cycle_id: str,
    agent_id: str,
    cleared_keys: list[str],
    scratch_hash_before: str,
) -> dict[str, Any]:
    return draft(
        "YSR_SCRATCH_CLEARED",
        {
            "cycle_id": cycle_id,
            "agent_id": agent_id,
            "scratch_cleared_keys": cleared_keys,
            "scratch_hash_before": scratch_hash_before,
            "observation_only": True,
        },
    )


def event_head_read(
    *,
    cycle_id: str,
    agent_id: str,
    prior_event_head: int | None,
    current_event_head: int | None,
    event_lag_count: int,
) -> dict[str, Any]:
    return draft(
        "YSR_EVENT_HEAD_READ",
        {
            "cycle_id": cycle_id,
            "agent_id": agent_id,
            "prior_event_head": prior_event_head,
            "current_event_head": current_event_head,
            "event_lag_count": event_lag_count,
            "observation_only": True,
        },
    )


def world_state_refreshed(
    *,
    cycle_id: str,
    agent_id: str,
    prior_hash: str,
    refreshed_hash: str,
) -> dict[str, Any]:
    return draft(
        "YSR_WORLD_STATE_REFRESHED",
        {
            "cycle_id": cycle_id,
            "agent_id": agent_id,
            "prior_world_state_hash": prior_hash,
            "refreshed_world_state_hash": refreshed_hash,
            "observation_only": True,
        },
    )


def memory_refs_refreshed(
    *,
    cycle_id: str,
    agent_id: str,
    memory_refs: list[str],
) -> dict[str, Any]:
    return draft(
        "YSR_MEMORY_REFS_REFRESHED",
        {
            "cycle_id": cycle_id,
            "agent_id": agent_id,
            "memory_refs_refreshed": memory_refs,
            "observation_only": True,
        },
    )


def resync_verified(cycle: YawnCycle, result: ResyncResult) -> dict[str, Any]:
    return draft(
        "YSR_RESYNC_VERIFIED",
        {
            "cycle": cycle.to_payload(),
            "resync": result.to_payload(),
            "observation_only": True,
        },
    )


def yawn_completed(cycle: YawnCycle) -> dict[str, Any]:
    return draft(
        "YSR_YAWN_COMPLETED",
        {
            "cycle": cycle.to_payload(),
            "observation_only": True,
        },
    )


def yawn_no_op(cycle: YawnCycle, *, reason: str) -> dict[str, Any]:
    return draft(
        "YSR_YAWN_NO_OP",
        {
            "cycle": cycle.to_payload(),
            "reason_code": reason,
            "observation_only": True,
        },
    )


def yawn_refused(*, agent_id: str, cycle_id: str, reason_code: str) -> dict[str, Any]:
    return draft(
        "YSR_YAWN_REFUSED",
        {
            "agent_id": agent_id,
            "cycle_id": cycle_id,
            "reason_code": reason_code,
            "observation_only": True,
        },
    )


def escalated_to_crr(*, agent_id: str, cycle_id: str, reason_code: str) -> dict[str, Any]:
    return draft(
        "YSR_ESCALATED_TO_CRR",
        {
            "agent_id": agent_id,
            "cycle_id": cycle_id,
            "reason_code": reason_code,
            "observation_only": True,
        },
    )


def yawn_failed(*, agent_id: str, cycle_id: str, reason_code: str) -> dict[str, Any]:
    return draft(
        "YSR_YAWN_FAILED",
        {
            "agent_id": agent_id,
            "cycle_id": cycle_id,
            "reason_code": reason_code,
            "observation_only": True,
        },
    )


__all__ = [
    "escalated_to_crr",
    "event_head_read",
    "memory_refs_refreshed",
    "resync_verified",
    "scratch_cleared",
    "scratch_snapshot_recorded",
    "world_state_refreshed",
    "yawn_completed",
    "yawn_failed",
    "yawn_no_op",
    "yawn_refused",
    "yawn_requested",
    "yawn_started",
]
