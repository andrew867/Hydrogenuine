"""HAL Phase 1 + GPP bind scaffold integration tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.governance.permit_binder import PermitBinder, descriptor_for
from hg_core.governance.rtc_bridge import emit_bind_result
from hg_core.governance.trace_emitter import TraceEmitter
from hg_core.governance.types import BindRequest
from hg_hal import arbitrate, decision_ref_for_result
from hg_hal.types import ArbitrationCandidate, ArbitrationRequest
from hg_runtime.bus import EventBus
from hg_runtime.handlers import Phase1HALDecisionHandler, StubCognitionHandler
from hg_runtime.handlers.stubs import StubKernelHandler, StubMemoryHandler, StubArousalReader, StubRecoveryHandler
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T14:00:{counter['value']:02d}.000000Z"

    return tick


def test_hal_result_referenced_by_gpp_bind_scaffold(tmp_path: Path):
    trace = TraceEmitter(tmp_path / "gpp" / "trace.jsonl", enabled=True, clock=_clock())
    binder = PermitBinder(trace_emitter=trace, clock=_clock())
    request = ArbitrationRequest(
        request_id="hal_req_gpp",
        proposal_ref="prop_gpp",
        candidates=(
            ArbitrationCandidate(
                candidate_id="cand_1",
                action_ref="act_1",
                capability_id="cap.oea_stub_log",
                effect_class="audit_log",
            ),
        ),
        context_refs=("evt_1",),
    )
    result = arbitrate(request)
    bind = binder.bind(
        BindRequest(
            request_id="dec_gpp_1",
            capability_id="cap.oea_stub_log",
            effect_class="audit_log",
            decision_ref=decision_ref_for_result(result),
        ),
        descriptor_for("cap.oea_stub_log"),
    )
    assert bind.permit is not None
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    events = emit_bind_result(bus, bind)
    assert [event["type"] for event in events] == ["GPP_TRACE_RECORDED", "GPP_PERMIT_BOUND"]


def test_hal_decision_handler_emits_hal_and_gpp_events(tmp_path: Path):
    trace = TraceEmitter(tmp_path / "gpp" / "trace.jsonl", enabled=True, clock=_clock())
    handler = Phase1HALDecisionHandler(permit_binder=PermitBinder(trace_emitter=trace, clock=_clock()))
    loop = RuntimeLoop(
        EventBus(tmp_path / "runtime", clock=_clock()),
        cognition=StubCognitionHandler(),
        decision=handler,
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
        {"session_id": "s1", "role": "user", "content": "hal"},
        source="plt.chat",
    )
    loop.run_once(poll_timeout=0.0)
    types = [event["type"] for event in loop.bus.read_all()]
    assert "HAL_ARBITRATION_REQUESTED" in types
    assert "HAL_ARBITRATION_RECORDED" in types
    assert "GPP_PERMIT_BOUND" in types
    assert "UEAK_EXECUTION_COMMITTED" in types
    assert types.index("HAL_ARBITRATION_REQUESTED") < types.index("HAL_ARBITRATION_RECORDED")
    assert types.index("HAL_ARBITRATION_RECORDED") < types.index("GPP_PERMIT_BOUND")
    decision = next(event for event in loop.bus.read_all() if event["type"] == "DECISION_EVENT")
    assert decision["payload"].get("hal_arbitration_ref")
    assert replay(tmp_path / "runtime").ok is True


def test_hal_handler_cannot_execute_action(tmp_path: Path):
  text = Path("hg_runtime/handlers/hal_decision.py").read_text(encoding="utf-8")
  forbidden = ("kernel.execute", "dispatch_committed", "hg_oea", "UEAKStub().execute")
  for token in forbidden:
      assert token not in text
