"""P32 model routing consolidation tests."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p32_consolidation_gate.py"
_spec = importlib.util.spec_from_file_location("p32_cons_gate", _GATE_PATH)
p32_cons_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p32_cons_gate)

from hg_runtime.model_routing.gate import validate_p32_consolidation_gate


# --- Full test suite run -----------------------------------------------------

class TestFullTestSuite:
    def test_all_p32_tests_pass(self):
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/autonomous_agent/test_p32_0_model_routing_schemas.py",
             "tests/autonomous_agent/test_p32_1_model_registry_preflight.py",
             "tests/autonomous_agent/test_p32_2_route_decision_refusal.py",
             "tests/autonomous_agent/test_p32_3_router_replay_soak.py",
             "-q", "--tb=short"],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"P32 tests failed:\n{result.stdout}\n{result.stderr}"


# --- Gate run ----------------------------------------------------------------

class TestP32ConsolidationGateRun:
    def test_gate_green(self):
        code, summary = p32_cons_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P32_MODEL_ROUTING_CONSOLIDATION"
        assert summary["ok"] is True
        assert summary["failures"] == []

    def test_all_sub_gates_green(self):
        _, summary = p32_cons_gate.run_gate()
        assert summary["p32_0_green"] is True
        assert summary["p32_1_green"] is True
        assert summary["p32_2_green"] is True
        assert summary["p32_3_green"] is True

    def test_p31_dependency(self):
        _, summary = p32_cons_gate.run_gate()
        assert summary["p31_consolidation_green"] is True

    def test_phase19_yellow(self):
        _, summary = p32_cons_gate.run_gate()
        assert summary["phase19_yellow_preserved"] is True

    def test_doctrine(self):
        _, summary = p32_cons_gate.run_gate()
        assert summary["model_selection_is_not_authority"] is True
        assert summary["routing_recommendation_is_advisory"] is True


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p32_0_green": True,
            "p32_1_green": True,
            "p32_2_green": True,
            "p32_3_green": True,
            "p31_consolidation_green": True,
            "model_selection_is_not_authority": True,
            "routing_recommendation_is_advisory": True,
            "no_providers_enabled": True,
            "no_route_reads_hg_local": True,
            "no_deletion": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "secret_redaction_passed": True,
            "proof_bundle_valid": True,
            "report_present": True,
        }
        data.update(overrides)
        return data

    def test_valid_passes(self):
        result = validate_p32_consolidation_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p32_0_fails(self):
        result = validate_p32_consolidation_gate(self._summary(p32_0_green=False))
        assert result["ok"] is False

    def test_missing_p31_fails(self):
        result = validate_p32_consolidation_gate(self._summary(p31_consolidation_green=False))
        assert result["ok"] is False

    def test_providers_enabled_fails(self):
        result = validate_p32_consolidation_gate(self._summary(no_providers_enabled=False))
        assert result["ok"] is False
