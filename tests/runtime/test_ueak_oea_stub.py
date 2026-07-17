from __future__ import annotations

import ast
from pathlib import Path

from hg_oea.stub import OEAStub
from hg_runtime.bus import EventBus
from hg_runtime.handlers import StubCognitionHandler, StubDecisionHandler, StubKernelHandler
from hg_runtime.replay import replay
from hg_ueak.stub import UEAKStub


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T05:00:{counter['value']:02d}.000000Z"

    return tick


def _decision(**action_overrides):
    action = {
        "action_type": "oea_stub_log",
        "capability_id": "cap.oea_stub_log",
        "effect_class": "audit_log",
        "summary": "demo",
    }
    action.update(action_overrides)
    return {
        "type": "DECISION_EVENT",
        "event_id": "evt_decision",
        "payload": {
            "decision_id": "dec_1",
            "proposal_id": "prop_1",
            "verdict": "allow_stub",
            "action": action,
        },
    }


def test_action_cannot_reach_oea_without_committed_event():
    oea = OEAStub()
    decision_only = [_decision()]
    assert oea.dispatch_committed(decision_only) == []
    assert oea.audit_records == []


def test_uncommitted_proposal_produces_no_oea_output():
    cognition = StubCognitionHandler()
    context = {
        "events": [{"event_id": "evt_1", "type": "CHAT_MESSAGE"}],
        "world_state": {},
        "memory": {},
        "arousal": {},
    }
    proposals = cognition.propose(context)
    assert proposals
    assert all(draft["type"] == "PROPOSAL_EMITTED" for draft in proposals)
    oea = OEAStub()
    assert oea.dispatch_committed([]) == []


def test_ueak_commit_then_oea_stub_audit(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    kernel = StubKernelHandler()
    drafts = kernel.execute([_decision()], {})
    types = [draft["type"] for draft in drafts]
    assert types == [
        "UEAK_EXECUTION_COMMITTED",
        "OEA_EFFECT_STUB_RECORDED",
        "EFFECT_RECEIPTED",
    ]
    for draft in drafts:
        bus.emit_draft(draft, source="handler:rtc.stub.kernel")
    event_types = [event["type"] for event in bus.read_all()]
    assert "UEAK_EXECUTION_COMMITTED" in event_types
    assert "OEA_EFFECT_STUB_RECORDED" in event_types
    assert "EFFECT_RECEIPTED" in event_types
    assert event_types.index("UEAK_EXECUTION_COMMITTED") < event_types.index(
        "OEA_EFFECT_STUB_RECORDED"
    )
    assert event_types.index("OEA_EFFECT_STUB_RECORDED") < event_types.index(
        "EFFECT_RECEIPTED"
    )


def test_cognition_handler_has_no_tool_handles():
    text = Path("hg_runtime/handlers/stubs.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    cognition_class = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "StubCognitionHandler"
    )
    for node in ast.walk(cognition_class):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and "tool" in target.id.lower():
                    raise AssertionError(f"unexpected tool handle {target.id}")


def test_replay_includes_committed_action_and_oea_stub_record(tmp_path: Path):
    from hg_runtime.handlers import (
        StubArousalReader,
        StubMemoryHandler,
        StubRecoveryHandler,
    )
    from hg_runtime.loop import RuntimeLoop

    bus = EventBus(tmp_path / "runtime", clock=_clock())
    loop = RuntimeLoop(
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
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "stub path"},
        source="plt.chat",
    )
    loop.run_once(poll_timeout=0.0)
    event_types = [event["type"] for event in loop.bus.read_all()]
    assert "UEAK_EXECUTION_COMMITTED" in event_types
    assert "OEA_EFFECT_STUB_RECORDED" in event_types
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["executions"]["committed"] == 1
    assert result.state["activity"]["executions"]["oea_stub_logged"] == 1
    assert result.state["activity"]["executions"]["receipted"] == 1


def test_ueak_stub_blocks_without_oea_on_deny():
    ueak = UEAKStub()
    ueak.block_all()
    drafts = ueak.execute([_decision()], {})
    assert drafts[0]["type"] == "UEAK_EXECUTION_DENIED"
    assert drafts[0]["payload"]["reason_code"] == "panic_blocked"
