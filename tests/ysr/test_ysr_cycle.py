"""YSR yawn soft-reset cycle tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hg_runtime import world_state as ws
from hg_runtime.bus import EventBus
from hg_runtime.contract import readonly_view
from hg_runtime.yawn.config import YSRConfig
from hg_runtime.yawn.handler import Phase1YSRHandler, StubYSRHandler
from hg_runtime.yawn.policy import evaluate_trigger
from hg_runtime.yawn.scratch import (
    ALLOWED_SCRATCH_KEYS,
    FORBIDDEN_SCRATCH_KEYS,
    clear_allowed_scratch,
    load_scratch,
    seed_transient_scratch,
    snapshot_scratch,
)
from hg_runtime.yawn.cycle import run_yawn_cycle, _bus_head_seq
from hg_runtime.replay import replay

YSR_TYPES = {
    "YSR_YAWN_REQUESTED",
    "YSR_YAWN_STARTED",
    "YSR_SCRATCH_SNAPSHOT_RECORDED",
    "YSR_SCRATCH_CLEARED",
    "YSR_EVENT_HEAD_READ",
    "YSR_WORLD_STATE_REFRESHED",
    "YSR_MEMORY_REFS_REFRESHED",
    "YSR_RESYNC_VERIFIED",
    "YSR_YAWN_COMPLETED",
    "YSR_YAWN_NO_OP",
    "YSR_YAWN_REFUSED",
    "YSR_ESCALATED_TO_CRR",
    "YSR_YAWN_FAILED",
}

FORBIDDEN_TYPES = {
    "DECISION_EVENT",
    "GPP_PERMIT_BOUND",
    "UEAK_EXECUTION_COMMITTED",
    "OEA_EXECUTION_COMPLETED",
    "TER_COMMAND_COMPLETED",
    "ACTION_COMMITTED",
}


def _submit_seed(bus: EventBus, count: int = 8) -> None:
    for i in range(count):
        bus.submit("TIMER_EVENT", {"i": i}, source="timer")


def _emit_seed(bus: EventBus, count: int = 8) -> None:
    _submit_seed(bus, count)
    bus.poll(timeout=0.0)


def test_disabled_ysr_is_safe_noop(ysr_bus, ysr_runtime_dir):
    handler = StubYSRHandler()
    view = readonly_view(ws.initial_state())
    assert handler.should_yawn(view, {}) is False
    assert handler.execute_yawn(view, {}) == []


def test_no_op_when_already_synced(ysr_runtime_dir, ysr_bus):
    cfg = YSRConfig(enabled=True, agent_ids=("agent0",), max_event_lag=25)
    handler = Phase1YSRHandler(config=cfg, runtime_dir=ysr_runtime_dir, clock=lambda: "2026-06-11T15:00:01.000000Z")
    handler.bind_runtime(ysr_bus, ws.initial_state())
    view = readonly_view(ws.initial_state())
    drafts = handler.execute_yawn(view, {}, operator_requested=False)
    no_ops = [d for d in drafts if d["type"] == "YSR_YAWN_NO_OP"]
    assert no_ops or not drafts


def test_triggers_on_event_lag(ysr_config, ysr_runtime_dir, ysr_bus, stale_scratch):
    _emit_seed(ysr_bus, 10)
    handler = Phase1YSRHandler(
        config=ysr_config,
        runtime_dir=ysr_runtime_dir,
        clock=lambda: "2026-06-11T15:00:02.000000Z",
        requested=True,
    )
    handler.bind_runtime(ysr_bus, ws.initial_state())
    view = readonly_view(ws.initial_state())
    drafts = handler.execute_yawn(view, {"max_severity": 0})
    types = [d["type"] for d in drafts]
    assert "YSR_YAWN_REQUESTED" in types
    assert "YSR_SCRATCH_SNAPSHOT_RECORDED" in types


def test_scratch_snapshot_before_clear(ysr_config, ysr_runtime_dir, ysr_bus, stale_scratch):
    _emit_seed(ysr_bus, 10)
    bus_head = _bus_head_seq(ysr_bus)
    drafts = run_yawn_cycle(
        config=ysr_config,
        agent_id="agent0",
        view=readonly_view(ws.initial_state()),
        aep_state={},
        bus=ysr_bus,
        runtime_dir=ysr_runtime_dir,
        clock_now="2026-06-11T15:00:03.000000Z",
        operator_requested=True,
    )
    snap_events = [d for d in drafts if d["type"] == "YSR_SCRATCH_SNAPSHOT_RECORDED"]
    clear_events = [d for d in drafts if d["type"] == "YSR_SCRATCH_CLEARED"]
    assert snap_events
    assert clear_events
    assert snap_events[0]["payload"]["event_head_seq"] < bus_head or snap_events[0]["payload"]["event_head_seq"] == 1


def test_clears_only_allowed_keys(ysr_runtime_dir, stale_scratch):
    cleared, _ = clear_allowed_scratch(ysr_runtime_dir, "agent0")
    for key in cleared:
        assert key in ALLOWED_SCRATCH_KEYS
    for forbidden in FORBIDDEN_SCRATCH_KEYS:
        assert forbidden not in cleared


def test_never_clears_forbidden_keys_in_store(ysr_runtime_dir):
    data = load_scratch(ysr_runtime_dir, "agent0")
    data["transient"]["ter_receipts"] = ["r1"]
    data["transient"]["transient_prompt_buffer"] = "x"
    from hg_runtime.yawn.scratch import save_scratch

    save_scratch(ysr_runtime_dir, "agent0", data)
    cleared, _ = clear_allowed_scratch(ysr_runtime_dir, "agent0")
    assert "ter_receipts" not in cleared
    after = load_scratch(ysr_runtime_dir, "agent0")
    assert after["transient"].get("ter_receipts") == ["r1"]


def test_reads_event_head(ysr_config, ysr_runtime_dir, ysr_bus, stale_scratch):
    _emit_seed(ysr_bus, 12)
    drafts = run_yawn_cycle(
        config=ysr_config,
        agent_id="agent0",
        view=readonly_view(ws.initial_state()),
        aep_state={},
        bus=ysr_bus,
        runtime_dir=ysr_runtime_dir,
        clock_now="2026-06-11T15:00:04.000000Z",
        operator_requested=True,
    )
    head_events = [d for d in drafts if d["type"] == "YSR_EVENT_HEAD_READ"]
    assert head_events
    assert head_events[0]["payload"]["current_event_head"] is not None


def test_refreshes_world_state_hash(ysr_config, ysr_runtime_dir, ysr_bus, stale_scratch):
    _emit_seed(ysr_bus, 10)
    drafts = run_yawn_cycle(
        config=ysr_config,
        agent_id="agent0",
        view=readonly_view(ws.initial_state()),
        aep_state={},
        bus=ysr_bus,
        runtime_dir=ysr_runtime_dir,
        clock_now="2026-06-11T15:00:05.000000Z",
        operator_requested=True,
    )
    ws_events = [d for d in drafts if d["type"] == "YSR_WORLD_STATE_REFRESHED"]
    assert ws_events
    assert ws_events[0]["payload"]["refreshed_world_state_hash"].startswith("sha256:")


def test_stale_drafts_invalidated_not_revived(ysr_config, ysr_runtime_dir, ysr_bus, stale_scratch):
    _emit_seed(ysr_bus, 10)
    drafts = run_yawn_cycle(
        config=ysr_config,
        agent_id="agent0",
        view=readonly_view(ws.initial_state()),
        aep_state={},
        bus=ysr_bus,
        runtime_dir=ysr_runtime_dir,
        clock_now="2026-06-11T15:00:07.000000Z",
        operator_requested=True,
    )
    resync = next(d for d in drafts if d["type"] == "YSR_RESYNC_VERIFIED")
    assert resync["payload"]["resync"]["stale_proposals_invalidated"] >= 1


def test_no_authority_freshened(ysr_config, ysr_runtime_dir, ysr_bus, stale_scratch):
    _emit_seed(ysr_bus, 10)
    drafts = run_yawn_cycle(
        config=ysr_config,
        agent_id="agent0",
        view=readonly_view(ws.initial_state()),
        aep_state={},
        bus=ysr_bus,
        runtime_dir=ysr_runtime_dir,
        clock_now="2026-06-11T15:00:06.000000Z",
        operator_requested=True,
    )
    for d in drafts:
        payload = d.get("payload", {})
        resync = payload.get("resync", {})
        assert resync.get("authority_freshened") is not True
        assert payload.get("authority") is None


def test_emits_ysr_events_only_in_loop(ysr_loop, ysr_bus, stale_scratch):
    _submit_seed(ysr_bus, 10)
    ysr_loop.bus.submit("TIMER_EVENT", {"trigger": True}, source="timer")
    ysr_loop.run_once(poll_timeout=0.0)
    ysr_events = [e["type"] for e in ysr_bus.read_all() if e["type"].startswith("YSR_")]
    assert ysr_events
    assert all(t in YSR_TYPES for t in ysr_events)
    assert not {e["type"] for e in ysr_bus.read_all()} & FORBIDDEN_TYPES


def test_world_state_reduces_ysr_events():
    state = ws.initial_state()
    for etype, extra in (
        ("YSR_YAWN_REQUESTED", {"cycle": {"agent_id": "agent0"}}),
        ("YSR_YAWN_COMPLETED", {"cycle": {"agent_id": "agent0", "cycle_id": "c1", "event_lag_count": 3}}),
        ("YSR_YAWN_REFUSED", {"agent_id": "agent0", "reason_code": "REFUSED_PANIC"}),
    ):
        event = {
            "event_id": f"id_{etype}",
            "type": etype,
            "seq": 1,
            "timestamp": "2026-06-11T15:00:01.000000Z",
            "payload": extra,
        }
        state = ws.apply(state, event)
    assert state["activity"]["ysr"]["requested"] == 1
    assert state["activity"]["ysr"]["completed"] == 1
    assert state["activity"]["ysr"]["refused"] == 1


def test_replay_deterministic(ysr_loop, ysr_bus, ysr_runtime_dir, stale_scratch):
    _submit_seed(ysr_bus, 8)
    ysr_loop.bus.submit("TIMER_EVENT", {"final": True}, source="timer")
    ysr_loop.run_once(poll_timeout=0.0)
    assert replay(ysr_runtime_dir).ok is True


def test_panic_refuses_ysr(ysr_handler, ysr_bus, ysr_runtime_dir, stale_scratch):
    _emit_seed(ysr_bus, 10)
    ysr_handler.bind_runtime(ysr_bus, ws.initial_state())
    view = readonly_view(ws.initial_state())
    assert ysr_handler.should_yawn(view, {}, panic_active=True) is False
    drafts = ysr_handler.execute_yawn(view, {}, panic_active=True, operator_requested=True)
    refused = [d for d in drafts if d["type"] == "YSR_YAWN_REFUSED"]
    assert any(d["payload"]["reason_code"] == "REFUSED_PANIC" for d in refused)


def test_crr_active_refuses_ysr(ysr_config, ysr_runtime_dir, ysr_bus):
    view_dict = ws.initial_state()
    view_dict["environment"]["recovery_state"] = "RECOVERY"
    decision = evaluate_trigger(
        config=ysr_config,
        agent_id="agent0",
        view=view_dict,
        aep_state={},
        runtime_dir=ysr_runtime_dir,
        bus_head_seq=10,
        prior_world_state_hash="sha256:a",
        refreshed_world_state_hash="sha256:b",
    )
    assert decision.result == "yawn_refused"
    assert decision.reason_code == "REFUSED_CRR_ACTIVE"


def test_aep_suggests_not_forces(ysr_config, ysr_runtime_dir):
    import time

    from hg_runtime.yawn.scratch import save_scratch

    seed_transient_scratch(ysr_runtime_dir, "agent0", event_head_seq=8)
    fresh = load_scratch(ysr_runtime_dir, "agent0")
    fresh["updated_at"] = int(time.time())
    save_scratch(ysr_runtime_dir, "agent0", fresh)
    decision = evaluate_trigger(
        config=ysr_config,
        agent_id="agent0",
        view=ws.initial_state(),
        aep_state={"max_severity": 6},
        runtime_dir=ysr_runtime_dir,
        bus_head_seq=10,
        prior_world_state_hash="sha256:a",
        refreshed_world_state_hash="sha256:a",
    )
    assert decision.result == "yawn_allowed"
    assert decision.reason_code == "aep_suggested"


def test_no_ter_oea_in_ysr_module():
    forbidden = ("hg_ter", "hg_oea", "hg_ueak", "hg_srp")
    for path in Path("hg_runtime/yawn").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(alias.name.startswith(p) for p in forbidden)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(node.module.startswith(p) for p in forbidden)


def test_stub_handler_noop():
    handler = StubYSRHandler()
    view = readonly_view(ws.initial_state())
    assert handler.should_yawn(view, {}) is False
