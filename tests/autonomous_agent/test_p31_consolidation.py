"""P31 evaluation harness consolidation tests."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p31_consolidation_gate.py"
_spec = importlib.util.spec_from_file_location("p31_cons_gate", _GATE_PATH)
p31_cons_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p31_cons_gate)

from hg_runtime.evaluation_harness.gate import validate_p31_consolidation_gate


# --- Full test suite run -----------------------------------------------------

class TestFullTestSuite:
    def test_all_p31_tests_pass(self):
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/autonomous_agent/test_p31_0_evaluation_harness_schemas.py",
             "tests/autonomous_agent/test_p31_1_task_family_fixture_runner.py",
             "tests/autonomous_agent/test_p31_2_competence_refusal_receipts.py",
             "tests/autonomous_agent/test_p31_3_evaluation_replay_soak.py",
             "-q", "--tb=short"],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"P31 tests failed:\n{result.stdout}\n{result.stderr}"


# --- Gate run ----------------------------------------------------------------

class TestP31ConsolidationGateRun:
    def test_gate_green(self):
        code, summary = p31_cons_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P31_EVALUATION_HARNESS_CONSOLIDATION"
        assert summary["ok"] is True
        assert summary["failures"] == []

    def test_all_sub_gates_green(self):
        _, summary = p31_cons_gate.run_gate()
        assert summary["p31_0_green"] is True
        assert summary["p31_1_green"] is True
        assert summary["p31_2_green"] is True
        assert summary["p31_3_green"] is True

    def test_prior_phases_green(self):
        _, summary = p31_cons_gate.run_gate()
        for key in ["p26_green", "p27_green", "p28_green", "p29_green", "p30_green"]:
            assert summary[key] is True, f"{key} not GREEN"

    def test_phase19_yellow(self):
        _, summary = p31_cons_gate.run_gate()
        assert summary["phase19_yellow_preserved"] is True

    def test_phase24_infra(self):
        _, summary = p31_cons_gate.run_gate()
        assert summary["phase24_infrastructure_only_preserved"] is True

    def test_doctrine_boundaries(self):
        _, summary = p31_cons_gate.run_gate()
        assert summary["evaluation_is_not_truth"] is True
        assert summary["evaluation_is_not_competence"] is True
        assert summary["benchmark_is_not_deployment_permission"] is True


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p31_0_green": True,
            "p31_1_green": True,
            "p31_2_green": True,
            "p31_3_green": True,
            "p26_green": True,
            "p27_green": True,
            "p28_green": True,
            "p29_green": True,
            "p30_green": True,
            "evaluation_is_not_truth": True,
            "evaluation_is_not_competence": True,
            "benchmark_is_not_deployment_permission": True,
            "expected_observed_match_is_not_truth": True,
            "no_live_effects": True,
            "no_web_provider": True,
            "no_pdf_ocr_html": True,
            "no_tool_authorization": True,
            "no_automatic_belief_promotion": True,
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
        result = validate_p31_consolidation_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p31_0_fails(self):
        result = validate_p31_consolidation_gate(self._summary(p31_0_green=False))
        assert result["ok"] is False

    def test_missing_p26_fails(self):
        result = validate_p31_consolidation_gate(self._summary(p26_green=False))
        assert result["ok"] is False

    def test_missing_no_deletion_fails(self):
        result = validate_p31_consolidation_gate(self._summary(no_deletion=False))
        assert result["ok"] is False
