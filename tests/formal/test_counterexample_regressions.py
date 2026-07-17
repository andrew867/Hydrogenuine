from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_learning.conformance.trace_checker import TraceConformanceChecker

ROOT = Path(__file__).resolve().parents[2]
CE_DIR = ROOT / "formal" / "conformance" / "counterexamples"


@pytest.fixture
def checker():
    return TraceConformanceChecker()


@pytest.mark.parametrize(
    "filename",
    [
        "ce_sg1_execute_without_decision.json",
        "ce_wd1_ladder_skip.json",
        "ce_hp4_resume_without_ack.json",
    ],
)
def test_counterexample_trace_rejected(checker, filename: str):
    data = json.loads((CE_DIR / filename).read_text(encoding="utf-8"))
    violations = checker.check_trace(data["events"])
    assert violations, f"expected rejection for {filename}"


def test_conformant_safety_gate_trace_accepted(checker):
    events = [
        {
            "component": "safety_gate",
            "event": "command_submitted",
            "timestamp": "2026-06-10T00:00:00Z",
            "robot_id": "r1",
        },
        {
            "component": "safety_gate",
            "event": "decision_approved",
            "timestamp": "2026-06-10T00:00:01Z",
            "robot_id": "r1",
        },
        {
            "component": "safety_gate",
            "event": "command_executed",
            "timestamp": "2026-06-10T00:00:02Z",
            "robot_id": "r1",
        },
    ]
    assert checker.check_trace(events) == []


def test_conformant_halt_protocol_trace(checker):
    events = [
        {
            "component": "halt_protocol",
            "event": "halt_triggered",
            "timestamp": "2026-06-10T00:00:00Z",
            "robot_id": "r1",
        },
        {
            "component": "halt_protocol",
            "event": "resume_requested",
            "timestamp": "2026-06-10T00:00:01Z",
            "robot_id": "r1",
        },
        {
            "component": "halt_protocol",
            "event": "resume_acknowledged",
            "timestamp": "2026-06-10T00:00:02Z",
            "robot_id": "r1",
        },
    ]
    assert checker.check_trace(events) == []
