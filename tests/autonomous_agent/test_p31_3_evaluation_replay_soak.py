"""P31-3 evaluation replay and soak tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p31_3_evaluation_replay_soak_gate.py"
_spec = importlib.util.spec_from_file_location("p31_3_gate", _GATE_PATH)
p31_3_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p31_3_gate)

from hg_runtime.evaluation_harness.evaluation_soak import run_soak
from hg_runtime.evaluation_harness.gate import validate_p31_3_gate


# --- Gate run ----------------------------------------------------------------

class TestP31_3GateRun:
    def test_gate_green(self):
        code, summary = p31_3_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P31_3_EVALUATION_HARNESS_SOAK"
        assert summary["ok"] is True
        assert summary["failures"] == []

    def test_gate_p31_2_dependency(self):
        _, summary = p31_3_gate.run_gate()
        assert summary["p31_2_green"] is True

    def test_gate_all_deterministic(self):
        _, summary = p31_3_gate.run_gate()
        assert summary["all_deterministic"] is True

    def test_gate_phase19_yellow(self):
        _, summary = p31_3_gate.run_gate()
        assert summary["phase19_yellow_preserved"] is True

    def test_gate_phase24_infra(self):
        _, summary = p31_3_gate.run_gate()
        assert summary["phase24_infrastructure_only_preserved"] is True


# --- Soak engine -------------------------------------------------------------

class TestSoak:
    def test_soak_deterministic(self):
        result = run_soak(iterations=3)
        assert result["run_deterministic"] is True
        assert result["replay_deterministic"] is True
        assert result["all_deterministic"] is True

    def test_soak_iterations_match(self):
        result = run_soak(iterations=2)
        assert result["iterations"] == 2
        assert len(result["iteration_hashes"]) == 2

    def test_soak_not_truth(self):
        result = run_soak(iterations=2)
        assert result["soak_is_not_truth"] is True
        assert result["soak_is_not_competence"] is True

    def test_soak_no_competence_claim(self):
        result = run_soak(iterations=2)
        assert result["competence_claimed"] is False
        assert result["evaluation_treated_as_truth"] is False


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p31_2_green": True,
            "iteration_count_met": True,
            "stable_hashes_match": True,
            "mutation_detected_fixture": True,
            "mutation_detected_expected_observed": True,
            "mutation_detected_fake_competence": True,
            "mutation_not_auto_repaired": True,
            "originals_not_mutated": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "secret_redaction_passed": True,
            "proof_bundle_valid": True,
            "report_present": True,
        }
        data.update(overrides)
        return data

    def test_valid_passes(self):
        result = validate_p31_3_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p31_2_fails(self):
        result = validate_p31_3_gate(self._summary(p31_2_green=False))
        assert result["ok"] is False

    def test_not_deterministic_fails(self):
        result = validate_p31_3_gate(self._summary(stable_hashes_match=False))
        assert result["ok"] is False
