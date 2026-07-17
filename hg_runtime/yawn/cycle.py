"""YSR yawn cycle orchestration."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from hg_runtime import world_state as ws
from hg_runtime.contract import jsonable, stable_id
from hg_runtime.yawn import rtc_bridge as rb
from hg_runtime.yawn.config import YSRConfig
from hg_runtime.yawn.policy import evaluate_trigger, should_escalate_to_crr
from hg_runtime.yawn.scratch import (
    clear_allowed_scratch,
    load_scratch,
    snapshot_scratch,
    update_scratch_head,
)
from hg_runtime.yawn.types import ResyncResult, YawnCycle


def _bus_head_seq(bus: Any) -> int:
    return max(0, int(getattr(bus, "next_seq", 1)) - 1)


def _refresh_world_state_from_bus(bus: Any) -> tuple[dict[str, Any], str]:
    events = list(bus.read_all())
    state = ws.apply_many(ws.initial_state(), events)
    return state, ws.state_hash(state)


def run_yawn_cycle(
    *,
    config: YSRConfig,
    agent_id: str,
    view: Mapping[str, Any],
    aep_state: Mapping[str, Any],
    bus: Any,
    runtime_dir: Any,
    clock_now: str,
    panic_active: bool = False,
    operator_requested: bool = False,
    prior_state: Mapping[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Run one yawn cycle for an agent; return RTC event drafts only."""
    drafts: List[Dict[str, Any]] = []
    bus_head = _bus_head_seq(bus)
    refreshed_state, refreshed_hash = _refresh_world_state_from_bus(bus)
    if prior_state is not None and isinstance(prior_state, dict):
        prior_hash = ws.state_hash(prior_state)
    else:
        prior_hash = ws.state_hash(jsonable(view))

    decision = evaluate_trigger(
        config=config,
        agent_id=agent_id,
        view=view,
        aep_state=aep_state,
        runtime_dir=runtime_dir,
        bus_head_seq=bus_head,
        prior_world_state_hash=prior_hash,
        refreshed_world_state_hash=refreshed_hash,
        panic_active=panic_active,
        operator_requested=operator_requested,
    )

    cycle_id = stable_id("ysr", agent_id, clock_now, bus_head)
    cycle = YawnCycle(
        cycle_id=cycle_id,
        agent_id=agent_id,
        requested_at=clock_now,
        reason_code=decision.reason_code,
    )

    if decision.result == "yawn_refused":
        drafts.append(rb.yawn_refused(agent_id=agent_id, cycle_id=cycle_id, reason_code=decision.reason_code))
        cycle.result_status = "REFUSED"
        cycle.completed_at = clock_now
        return drafts

    if decision.result == "no_op_already_synced":
        cycle.result_status = "NO_OP_ALREADY_SYNCED"
        cycle.completed_at = clock_now
        cycle.prior_event_head = int(load_scratch(runtime_dir, agent_id).get("event_head_seq", 0) or 0)
        cycle.current_event_head = bus_head
        drafts.append(rb.yawn_no_op(cycle, reason=decision.reason_code))
        return drafts

    scratch_before = load_scratch(runtime_dir, agent_id)
    cycle.prior_event_head = int(scratch_before.get("event_head_seq", 0) or 0)
    cycle.event_lag_count = max(0, bus_head - (cycle.prior_event_head or 0))
    cycle.prior_world_state_hash = prior_hash

    cycle.result_status = "YAWN_REQUESTED"
    drafts.append(rb.yawn_requested(cycle, reason=decision.reason_code))
    cycle.result_status = "PAUSING"
    drafts.append(rb.yawn_started(cycle))

    snap = snapshot_scratch(runtime_dir, agent_id)
    cycle.scratch_hash_before = snap.scratch_hash
    cycle.result_status = "SCRATCH_SNAPSHOT_RECORDED"
    drafts.append(rb.scratch_snapshot_recorded(snap, cycle_id=cycle_id))

    cleared, before_hash = clear_allowed_scratch(
        runtime_dir,
        agent_id,
        clear_transient=config.clear_transient_buffers,
    )
    cycle.scratch_cleared_keys = cleared
    cycle.result_status = "SCRATCH_CLEARED"
    drafts.append(
        rb.scratch_cleared(
            cycle_id=cycle_id,
            agent_id=agent_id,
            cleared_keys=cleared,
            scratch_hash_before=before_hash,
        )
    )

    cycle.current_event_head = bus_head
    cycle.result_status = "EVENT_HEAD_READ"
    drafts.append(
        rb.event_head_read(
            cycle_id=cycle_id,
            agent_id=agent_id,
            prior_event_head=cycle.prior_event_head,
            current_event_head=cycle.current_event_head,
            event_lag_count=cycle.event_lag_count,
        )
    )

    cycle.refreshed_world_state_hash = refreshed_hash
    cycle.result_status = "WORLD_STATE_REFRESHED"
    drafts.append(
        rb.world_state_refreshed(
            cycle_id=cycle_id,
            agent_id=agent_id,
            prior_hash=prior_hash,
            refreshed_hash=refreshed_hash,
        )
    )

    memory_refs = [f"ysr:{agent_id}:head:{bus_head}"]
    cycle.memory_refs_refreshed = memory_refs
    cycle.result_status = "MEMORY_REFS_REFRESHED"
    drafts.append(
        rb.memory_refs_refreshed(
            cycle_id=cycle_id,
            agent_id=agent_id,
            memory_refs=memory_refs,
        )
    )

    stale_count = len(cleared)
    drafts_before = scratch_before.get("transient", {}).get("uncommitted_proposal_drafts", [])
    if isinstance(drafts_before, list):
        stale_count = sum(1 for d in drafts_before if isinstance(d, dict))
    event_count_before = len(list(bus.read_all()))
    update_scratch_head(runtime_dir, agent_id, bus_head)
    event_count_after = len(list(bus.read_all()))

    resync_ok = event_count_before == event_count_after and cycle.current_event_head == bus_head

    resync = ResyncResult(
        ok=resync_ok,
        prior_event_head=cycle.prior_event_head,
        current_event_head=cycle.current_event_head,
        prior_world_state_hash=prior_hash,
        refreshed_world_state_hash=refreshed_hash,
        event_log_mutated=event_count_before != event_count_after,
        authority_freshened=False,
        receipts_deleted=False,
        stale_proposals_invalidated=stale_count,
        reason_code=None if resync_ok else "resync_verify_failed",
    )

    cycle.result_status = "RESYNC_VERIFIED"
    drafts.append(rb.resync_verified(cycle, resync))

    if not resync_ok:
        cycle.result_status = "FAILED"
        cycle.completed_at = clock_now
        drafts.append(rb.yawn_failed(agent_id=agent_id, cycle_id=cycle_id, reason_code="resync_verify_failed"))
        if should_escalate_to_crr(config=config, event_lag=cycle.event_lag_count, resync_ok=False):
            drafts.append(rb.escalated_to_crr(agent_id=agent_id, cycle_id=cycle_id, reason_code="resync_failed"))
        return drafts

    cycle.result_status = "RESUMED"
    cycle.completed_at = clock_now
    drafts.append(rb.yawn_completed(cycle))
    return drafts


def run_yawn_for_agents(
    *,
    config: YSRConfig,
    agent_ids: Sequence[str],
    view: Mapping[str, Any],
    aep_state: Mapping[str, Any],
    bus: Any,
    runtime_dir: Any,
    clock_now: str,
    panic_active: bool = False,
    operator_requested: bool = False,
    prior_state: Mapping[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    all_drafts: List[Dict[str, Any]] = []
    for agent_id in agent_ids:
        all_drafts.extend(
            run_yawn_cycle(
                config=config,
                agent_id=agent_id,
                view=view,
                aep_state=aep_state,
                bus=bus,
                runtime_dir=runtime_dir,
                clock_now=clock_now,
                panic_active=panic_active,
                operator_requested=operator_requested,
                prior_state=prior_state,
            )
        )
    return all_drafts


__all__ = ["run_yawn_cycle", "run_yawn_for_agents", "_bus_head_seq", "_refresh_world_state_from_bus"]
