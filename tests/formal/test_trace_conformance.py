from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hg_learning.conformance.trace_checker import TraceConformanceChecker

ROOT = Path(__file__).resolve().parents[2]


def test_automaton_file_exists():
    path = ROOT / "formal" / "conformance" / "safety_gate_automaton.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "safety_gate" in data["components"]
    assert "watchdog" in data["components"]
    assert "halt_protocol" in data["components"]


def test_regen_script_invariants():
    result = subprocess.run(
        [sys.executable, str(ROOT / "formal" / "conformance" / "regen_conformance_automaton.py"), "--check-invariants"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_tla_sources_present():
    for rel in [
        "formal/safety_gate/SafetyGate.tla",
        "formal/watchdog/Watchdog.tla",
        "formal/halt/HaltProtocol.tla",
        "formal/composition/GateMeshComposition.tla",
    ]:
        assert (ROOT / rel).exists(), rel


def test_invalid_transition_rejected():
    checker = TraceConformanceChecker()
    err = checker.check_event({
        "component": "safety_gate",
        "event": "level_escalated",
        "timestamp": "2026-01-01T00:00:00Z",
        "robot_id": "r1",
    })
    assert err is not None


def test_hg_learning_import_path():
    from hg_learning.conformance import TraceConformanceChecker as TC2

    assert TC2 is TraceConformanceChecker
