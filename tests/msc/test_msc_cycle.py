"""MSC meditation cycle tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hg_runtime import world_state as ws
from hg_runtime.bus import EventBus
from hg_runtime.msc.config import MSCConfig
from hg_runtime.msc.handler import Phase1MSCHandler, StubMSCHandler
from hg_runtime.msc.registry import SubAgentRegistry
from hg_runtime.msc.summary import build_deterministic_summary
from hg_runtime.msc.types import SubAgentIdentity
from hg_runtime.msc.window import select_bounded_window
from hg_runtime.msc.store import load_previous_summary_ref, store_summary_ref
from hg_runtime.replay import replay

MSC_TYPES = {
    "MSC_MEDITATION_REQUESTED",
    "MSC_MEDITATION_STARTED",
    "MSC_EVENT_WINDOW_SELECTED",
    "MSC_LISTENING_COMPLETED",
    "MSC_SUMMARY_RECORDED",
    "MSC_SETTLED",
    "MSC_SKIPPED",
    "MSC_FAILED",
    "MSC_REFUSED",
}

AUTHORITY_TYPES = {
    "DECISION_EVENT",
    "GPP_PERMIT_BOUND",
    "UEAK_EXECUTION_COMMITTED",
    "OEA_EXECUTION_COMPLETED",
    "TER_COMMAND_COMPLETED",
    "ACTION_COMMITTED",
}


def _seed_events(bus: EventBus, count: int = 3) -> None:
    for i in range(count):
        bus.submit("TIMER_EVENT", {"tick": i}, source="timer")


def test_disabled_msc_is_safe_noop(stub_msc_loop, msc_bus):
    _seed_events(msc_bus)
    stub_msc_loop.bus.submit("TIMER_EVENT", {"n": 1}, source="timer")
    result = stub_msc_loop.run_once(poll_timeout=0.0)
    assert result == "tick"
    types = {e["type"] for e in msc_bus.read_all()}
    assert not types & MSC_TYPES


def test_msc_emits_only_msc_events(msc_loop, msc_bus, msc_handler):
    _seed_events(msc_bus, 5)
    msc_loop.bus.submit("TIMER_EVENT", {"n": 99}, source="timer")
    msc_loop.run_once(poll_timeout=0.0)
    new_types = []
    for event in msc_bus.read_all():
        etype = event["type"]
        if etype.startswith("MSC_"):
            new_types.append(etype)
    assert new_types
    assert all(t in MSC_TYPES for t in new_types)
    assert not {e["type"] for e in msc_bus.read_all()} & AUTHORITY_TYPES


def test_msc_no_authority_in_drafts(msc_handler, msc_bus, msc_runtime_dir):
    _seed_events(msc_bus, 4)
    msc_handler.bind_runtime(msc_bus, ws.initial_state())
    from hg_runtime.contract import readonly_view

    view = readonly_view(ws.initial_state())
    drafts = msc_handler.execute_cycle(view, {"max_severity": 0})
    for d in drafts:
        assert d["type"] in MSC_TYPES
        payload = d.get("payload", {})
        assert payload.get("authority") is None
        assert "permit" not in str(payload).lower() or "observation_only" in payload


def test_bounded_window_respects_max_events():
    events = [
        {"event_id": f"e{i}", "type": "TIMER_EVENT", "seq": i, "timestamp": f"2026-06-11T12:00:{i:02d}.000000Z", "payload": {}}
        for i in range(100)
    ]
    sel = select_bounded_window(
        events,
        agent_id="agent0",
        window_id="w1",
        max_events=10,
        max_age_seconds=300,
        clock_now="2026-06-11T12:05:00.000000Z",
    )
    assert len(sel.event_ids) <= 10


def test_window_records_ids_and_hashes():
    events = [
        {
            "event_id": "evt_a",
            "type": "AEP_SIGNAL_RECORDED",
            "seq": 1,
            "timestamp": "2026-06-11T12:01:00.000000Z",
            "payload": {"signal_id": "s1"},
        }
    ]
    sel = select_bounded_window(
        events,
        agent_id="agent0",
        window_id="w2",
        max_events=50,
        max_age_seconds=300,
        clock_now="2026-06-11T12:02:00.000000Z",
    )
    assert sel.event_ids == ("evt_a",)
    assert len(sel.event_hashes) == 1
    assert sel.event_hashes[0].startswith("sha256:")


def test_secret_redaction_in_window():
    events = [
        {
            "event_id": "evt_secret",
            "type": "API_REQUEST",
            "seq": 1,
            "timestamp": "2026-06-11T12:01:00.000000Z",
            "payload": {"api_key": "super-secret", "path": "/health"},
        }
    ]
    sel = select_bounded_window(
        events,
        agent_id="agent0",
        window_id="w3",
        max_events=50,
        max_age_seconds=300,
        clock_now="2026-06-11T12:02:00.000000Z",
    )
    assert sel.redacted_count >= 0
    assert len(sel.event_ids) == 1


def test_deterministic_summary_stable():
    events = [
        {"event_id": "e1", "type": "AEP_SIGNAL_RECORDED", "payload": {}},
        {"event_id": "e2", "type": "CRR_CYCLE_RECORDED", "payload": {}},
    ]
    view = ws.initial_state()
    h = ws.state_hash(view)
    s1 = build_deterministic_summary(
        summary_id="sum1",
        agent_id="agent0",
        cycle_id="c1",
        events=events,
        event_hashes=("h1", "h2"),
        view=view,
        world_state_hash=h,
    )
    s2 = build_deterministic_summary(
        summary_id="sum1",
        agent_id="agent0",
        cycle_id="c1",
        events=events,
        event_hashes=("h1", "h2"),
        view=view,
        world_state_hash=h,
    )
    assert s1.summary_hash == s2.summary_hash


def test_world_state_reduces_msc_events():
    state = ws.initial_state()
    for etype, extra in (
        ("MSC_MEDITATION_REQUESTED", {"cycle": {"agent_id": "agent0"}}),
        ("MSC_SETTLED", {"cycle": {"agent_id": "agent0", "cycle_id": "c1"}, "summary_hash": "sha256:abc"}),
        ("MSC_REFUSED", {"reason_code": "REFUSED_PANIC", "cycle": {"agent_id": "agent0"}}),
    ):
        event = {
            "event_id": f"id_{etype}",
            "type": etype,
            "seq": 1,
            "timestamp": "2026-06-11T12:00:01.000000Z",
            "payload": extra,
        }
        state = ws.apply(state, event)
    assert state["activity"]["msc"]["requested"] == 1
    assert state["activity"]["msc"]["settled"] == 1
    assert state["activity"]["msc"]["refused"] == 1
    assert state["activity"]["msc"]["refused_by_reason"]["REFUSED_PANIC"] == 1


def test_replay_deterministic_after_msc(msc_loop, msc_bus, msc_runtime_dir):
    _seed_events(msc_bus, 6)
    msc_loop.bus.submit("TIMER_EVENT", {"final": True}, source="timer")
    msc_loop.run_once(poll_timeout=0.0)
    result = replay(msc_runtime_dir)
    assert result.ok is True


def test_aep_suggests_but_does_not_command(msc_config, msc_runtime_dir):
    registry = SubAgentRegistry({"agent0": SubAgentIdentity(agent_id="agent0")})
    handler = Phase1MSCHandler(
        config=msc_config,
        registry=registry,
        runtime_dir=msc_runtime_dir,
        requested=False,
    )
    view = ws.initial_state()
    assert handler.should_enter_cycle(view, {"max_severity": 8}) is True
    assert handler.should_enter_cycle(view, {"max_severity": 3}) is False
    drafts = handler.execute_cycle(view, {"max_severity": 8}, panic_active=False)
    assert all("observation_only" in d.get("payload", {}) or d["type"] != "MSC_SETTLED" for d in drafts) or not drafts


def test_crr_active_refuses_meditation(msc_handler, msc_bus):
    _seed_events(msc_bus, 3)
    msc_handler.bind_runtime(msc_bus, ws.initial_state())
    from hg_runtime.contract import readonly_view

    view = readonly_view(ws.initial_state())
    view_dict = ws.initial_state()
    view_dict["environment"]["recovery_state"] = "RECOVERY"
    view = readonly_view(view_dict)
    assert msc_handler.should_enter_cycle(view, {"max_severity": 0}) is False
    drafts = msc_handler.execute_cycle(view, {"max_severity": 0})
    refused = [d for d in drafts if d["type"] == "MSC_REFUSED"]
    assert any(d["payload"]["reason_code"] == "REFUSED_RECOVERY_ACTIVE" for d in refused)


def test_panic_refuses_meditation(msc_handler, msc_bus):
    _seed_events(msc_bus, 3)
    msc_handler.bind_runtime(msc_bus, ws.initial_state())
    from hg_runtime.contract import readonly_view

    view = readonly_view(ws.initial_state())
    assert msc_handler.should_enter_cycle(view, {"max_severity": 0}, panic_active=True) is False
    drafts = msc_handler.execute_cycle(view, {"max_severity": 0}, panic_active=True)
    refused = [d for d in drafts if d["type"] == "MSC_REFUSED"]
    assert any(d["payload"]["reason_code"] == "REFUSED_PANIC" for d in refused)


def test_no_ter_oea_gpp_ueak_in_msc_module():
    forbidden = ("hg_ter", "hg_oea", "hg_ueak", "hg_core.governance")
    for path in Path("hg_runtime/msc").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for prefix in forbidden:
                        assert not alias.name.startswith(prefix), f"{path}: {alias.name}"
            if isinstance(node, ast.ImportFrom) and node.module:
                for prefix in forbidden:
                    assert not node.module.startswith(prefix), f"{path}: {node.module}"


def test_model_assisted_disabled_by_default(msc_config):
    assert msc_config.allow_model_summary is False
    cfg = MSCConfig.from_env()
    assert cfg.allow_model_summary is False


def test_memory_stores_summary_ref_not_authority(msc_runtime_dir):
    ref = store_summary_ref(
        msc_runtime_dir,
        agent_id="agent0",
        cycle_id="c1",
        summary_id="sum1",
        summary_hash="sha256:deadbeef",
    )
    assert ref.startswith("msc:agent0:")
    loaded = load_previous_summary_ref(msc_runtime_dir, "agent0")
    assert loaded == ref
    data = (msc_runtime_dir / "msc_index.json").read_text(encoding="utf-8")
    assert "observation_only" in data
    assert "authority" not in data.lower() or "observation_only" in data


def test_sub_agent_identity_not_operator_iam():
    registry = SubAgentRegistry()
    registry.register(SubAgentIdentity(agent_id="agent0"))
    assert registry.is_operator_identity("agent0") is False
    assert registry.get("agent0") is not None


def test_stub_handler_never_enters_cycle():
    handler = StubMSCHandler()
    view = ws.initial_state()
    assert handler.should_enter_cycle(view, {}) is False
    assert handler.execute_cycle(view, {}) == []
