"""P32-3 router replay and soak tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p32_3_router_replay_soak_gate.py"
_spec = importlib.util.spec_from_file_location("p32_3_gate", _GATE_PATH)
p32_3_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p32_3_gate)

from hg_runtime.model_routing.routing_soak import run_routing_soak
from hg_runtime.model_routing.gate import validate_p32_3_gate


# --- Gate run ----------------------------------------------------------------

class TestP32_3GateRun:
    def test_gate_green(self):
        code, summary = p32_3_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P32_3_ROUTER_REPLAY_SOAK"
        assert summary["ok"] is True

    def test_p32_2_dependency(self):
        _, summary = p32_3_gate.run_gate()
        assert summary["p32_2_green"] is True

    def test_deterministic(self):
        _, summary = p32_3_gate.run_gate()
        assert summary["replay_deterministic"] is True
        assert summary["soak_passed"] is True

    def test_phase19_yellow(self):
        _, summary = p32_3_gate.run_gate()
        assert summary["phase19_yellow_preserved"] is True


# --- Soak engine -------------------------------------------------------------

class TestRoutingSoak:
    def test_deterministic(self):
        result = run_routing_soak(iterations=3)
        assert result["deterministic"] is True
        assert result["unique_hashes"] == 1

    def test_iterations_match(self):
        result = run_routing_soak(iterations=2)
        assert result["iterations"] == 2
        assert len(result["iteration_hashes"]) == 2

    def test_not_authority(self):
        result = run_routing_soak(iterations=2)
        assert result["soak_is_not_authority"] is True
        assert result["routing_recommendation_is_advisory"] is True


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p32_2_green": True,
            "replay_deterministic": True,
            "soak_passed": True,
            "no_providers_enabled": True,
            "no_route_reads_hg_local": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "secret_redaction_passed": True,
            "proof_bundle_valid": True,
            "report_present": True,
        }
        data.update(overrides)
        return data

    def test_valid_passes(self):
        result = validate_p32_3_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p32_2_fails(self):
        result = validate_p32_3_gate(self._summary(p32_2_green=False))
        assert result["ok"] is False

    def test_not_deterministic_fails(self):
        result = validate_p32_3_gate(self._summary(replay_deterministic=False))
        assert result["ok"] is False
