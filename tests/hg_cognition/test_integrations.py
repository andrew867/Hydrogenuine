"""Integration tests: TraceStore, ArtifactStore, PersonaStore, meditation with in-memory stores."""
import time
import tempfile
import os
from hg_cognition.schemas.trace import StepTrace, ToolCallTrace
from hg_cognition.schemas.common import MeditationReport
from hg_cognition.workflows.meditation import run_meditation
from hg_cognition.persona.quad import QuadCoords
from hg_cognition.integrations.memory_impls import (
    InMemoryTraceStore,
    JsonlArtifactStore,
    InMemoryPersonaStore,
)
from hg_cognition.integrations.interfaces import TraceStore, ArtifactStore, PersonaStore


def test_trace_store_returns_step_trace_list():
    now = time.time()
    steps = [
        StepTrace(now, "c1", "r1", "n1", "a", "agent", "", "out", [], [], 0, 0, 0, [], None),
    ]
    store = InMemoryTraceStore(steps)
    out = store.fetch_window(correlation_id="c1", start_ts=now - 1, end_ts=now + 1)
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0].correlation_id == "c1"


def test_artifact_store_persists_meditation_report():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        store = JsonlArtifactStore(path)
        report = MeditationReport(
            report_id="rid1",
            correlation_id="c1",
            window_start_ts=0.0,
            window_end_ts=1.0,
            scores=[],
            persona_updates={},
            signature_updates={},
            contradictions=[],
            steering_recommendations=[],
            summary="test",
        )
        store.write_report(report)
        store.write_report(report)
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert "rid1" in lines[0]
    finally:
        os.unlink(path)


def test_persona_store_load_save_round_trip():
    store = InMemoryPersonaStore()
    hist = [{"x": 0.0, "y": 0.0, "confidence": 0.2}]
    store.save_history("agent1", hist)
    loaded = store.load_history("agent1")
    assert loaded == hist
    assert store.load_history("missing") == []


def test_meditation_run_with_in_memory_stores():
    now = time.time()
    steps = [
        StepTrace(
            now - 2, "c1", "r1", "n1", "human", "human",
            "safe research", "", ["safe"], ["safe"], 1, 1, 2, [], None,
        ),
        StepTrace(
            now - 1, "c1", "r1", "n2", "agent", "agent",
            "", "Done.", ["safe"], ["safe"], 0, 0, 0, [], None,
        ),
    ]
    trace_store = InMemoryTraceStore(steps)
    window = trace_store.fetch_window(correlation_id="c1", start_ts=now - 5, end_ts=now + 1)
    persona_store = InMemoryPersonaStore()
    persona_store.save_history("human", [QuadCoords(0, 0, 0.2)])
    persona_store.save_history("agent", [QuadCoords(0, 0, 0.2)])
    persona_history = {aid: [QuadCoords(0, 0, 0.2)] for aid in ["human", "agent"]}
    report = run_meditation(
        steps=window,
        baseline_intent_text=steps[0].input_text,
        baseline_response_text="safe",
        denied_intent_texts=[],
        persona_history=persona_history,
    )
    assert report.report_id
    assert isinstance(report.scores, list)
    assert report.summary
