"""Regulation stack integration drift coverage."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hg_aep.types import AUTHORITY_FIELD_NAMES
from hg_crr.executors import EXECUTOR_REGISTRY
from hg_runtime.bus import EventBus
from hg_runtime.handlers import (
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
    StubArousalReader,
    StubRecoveryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay
from hg_runtime import world_state as ws


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T06:00:{counter['value']:02d}.000000Z"

    return tick


def _loop(tmp_path: Path) -> RuntimeLoop:
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    return RuntimeLoop(
        bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )


def test_no_rtc_bus_bypass_in_regulation_modules():
    forbidden = ("bus.emit(", "EventBus(")
    for package in ("hg_crr", "hg_aep"):
        for path in Path(package).rglob("*.py"):
            if path.name.endswith("rtc_adapter.py") or path.name.endswith("rtc_bridge.py"):
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, f"{path} must not bypass RTC bus via {token}"


def test_committed_actions_require_ueak_before_oea(tmp_path: Path):
    loop = _loop(tmp_path)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "path"},
        source="plt.chat",
    )
    loop.run_once(poll_timeout=0.0)
    types = [event["type"] for event in loop.bus.read_all()]
    assert "UEAK_EXECUTION_COMMITTED" in types
    assert "OEA_EFFECT_STUB_RECORDED" in types
    assert "EFFECT_RECEIPTED" in types
    assert types.index("UEAK_EXECUTION_COMMITTED") < types.index("OEA_EFFECT_STUB_RECORDED")
    assert types.index("OEA_EFFECT_STUB_RECORDED") < types.index("EFFECT_RECEIPTED")


def test_gpp_trace_refs_remain_hash_only(tmp_path: Path):
    from hg_core.governance.trace_emitter import TraceEmitter

    trace = TraceEmitter(tmp_path / "gpp" / "governance_trace.jsonl", enabled=True, clock=_clock())
    loop = _loop(tmp_path)
    loop.governance_trace = trace
    loop.bus.submit("CHAT_MESSAGE", {"session_id": "s1", "content": "trace"}, source="plt.chat")
    loop.run_once(poll_timeout=0.0)
    trace_events = [
        event for event in loop.bus.read_all() if event["type"] == "GOVERNANCE_TRACE_RECORDED"
    ]
    assert trace_events
    assert trace_events[0]["payload"]["enforcement"] == "none_phase0_trace_only"


def test_aep_has_no_authority_fields_in_schema():
    import json

    schema = json.loads(Path("docs/schemas/aep_signal_v1.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert AUTHORITY_FIELD_NAMES.isdisjoint(schema["properties"])


def test_crr_does_not_duplicate_hygiene_executors():
    import re

    call_pattern = re.compile(
        r"\b(run_gc_for_agent|run_retention_job|_evict_expired|compact_session)\s*\("
    )
    implementation_files = [
        path
        for path in Path("hg_crr").glob("*.py")
        if path.name not in {"executors.py", "__init__.py"}
    ]
    for path in implementation_files:
        assert not call_pattern.search(path.read_text(encoding="utf-8")), (
            f"{path} must not invoke hygiene executors directly"
        )
    assert EXECUTOR_REGISTRY
    assert all(ref.phase0_status == "registered_not_invoked" for ref in EXECUTOR_REGISTRY)


def test_cognition_has_no_tool_handles():
    cognition = StubCognitionHandler()
    assert not hasattr(cognition, "tools")
    assert not hasattr(cognition, "tool_handles")


def test_world_state_reconstructable_from_event_log(tmp_path: Path):
    loop = _loop(tmp_path)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "drift"}, source="timer")
    loop.run_once(poll_timeout=0.0)
    events = list(loop.bus.read_all())
    rebuilt = ws.apply_many(ws.initial_state(), events)
    assert ws.state_hash(rebuilt) == ws.state_hash(loop.state)


def test_replay_is_deterministic(tmp_path: Path):
    loop = _loop(tmp_path)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "drift"}, source="timer")
    loop.run_once(poll_timeout=0.0)
    first = replay(tmp_path / "runtime")
    second = replay(tmp_path / "runtime")
    assert first.ok and second.ok
    assert first.state_hash == second.state_hash


def test_no_real_external_side_effects_in_oea_stub():
    text = Path("hg_oea/stub.py").read_text(encoding="utf-8")
    forbidden = ("requests.", "httpx.", "urllib.", "subprocess.", "socket.")
    for token in forbidden:
        assert token not in text


def test_architecture_static_fences():
    aep_text = Path("hg_aep/types.py").read_text(encoding="utf-8")
    assert "AUTHORITY_FIELD_NAMES" in aep_text
    loop_text = Path("hg_runtime/loop.py").read_text(encoding="utf-8")
    assert "no loop-level OEA call exists" in loop_text
    assert "hg_srp" not in loop_text


def test_srp_skeleton_runs_above_runtime_loop_not_inside(tmp_path: Path):
    from hg_srp import emit_skeleton_cycle

    bus = EventBus(tmp_path / "runtime", clock=_clock())
    emit_skeleton_cycle(bus, tmp_path / "srp", observed_at="2026-06-11T06:00:00.000000Z")
    events = list(bus.read_all())
    assert [event["type"] for event in events] == [
        "SRP_DRIFT_OBSERVED",
        "GAP_DETECTED",
        "SRP_REPAIR_PROPOSED",
    ]
    assert list(events[1]["causal_parents"]) == [events[0]["event_id"]]
    assert list(events[2]["causal_parents"]) == [events[1]["event_id"]]
    assert replay(tmp_path / "runtime").ok is True


def test_srp_unsigned_apply_stays_rejected(tmp_path: Path):
    from hg_srp import RepairProposal, SRPSkeletonLoop, attempt_bundle_apply

    payload = SRPSkeletonLoop(tmp_path / "srp").run_once(observed_at="2026-06-11T06:00:00.000000Z")[-1][
        "payload"
    ]
    proposal = RepairProposal(
        proposal_id=payload["proposal_id"],
        drift_ref=payload["drift_ref"],
        gap_ref=payload["gap_ref"],
        target_files=tuple(payload["target_files"]),
        intended_change_summary=payload["intended_change_summary"],
        test_plan=payload["test_plan"],
        risk_notes=payload["risk_notes"],
        created_at=payload["created_at"],
    )
    assert attempt_bundle_apply(proposal).ok is False


def test_streaming_cognition_handler_has_no_tool_handles():
    from hg_runtime.cognition import StreamingCognitionHandler
    from hg_runtime.cognition.fake_provider import FakeModelProvider

    handler = StreamingCognitionHandler(provider=FakeModelProvider())
    assert not hasattr(handler, "tools")
    assert not hasattr(handler, "tool_handles")
