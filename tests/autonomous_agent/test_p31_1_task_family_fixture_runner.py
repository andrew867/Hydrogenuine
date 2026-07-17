"""P31-1 task family fixture runner tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p31_1_task_family_runner_gate.py"
_spec = importlib.util.spec_from_file_location("p31_1_gate", _GATE_PATH)
p31_1_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p31_1_gate)

from hg_runtime.evaluation_harness.schemas import TASK_FAMILIES
from hg_runtime.evaluation_harness.fixtures import builtin_fixtures
from hg_runtime.evaluation_harness.fixture_runner import evaluate_fixture, run_fixtures
from hg_runtime.evaluation_harness.evaluation_replay import replay_evaluation
from hg_runtime.evaluation_harness.task_family_matrix import (
    TASK_FAMILY_MATRIX,
    get_coverage,
    get_family_spec,
)
from hg_runtime.evaluation_harness.evaluation_artifact_writer import write_evaluation_artifacts
from hg_runtime.evaluation_harness.gate import validate_p31_1_gate


# --- Gate run ----------------------------------------------------------------

class TestP31_1GateRun:
    def test_gate_green(self):
        code, summary = p31_1_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P31_1_TASK_FAMILY_FIXTURE_RUNNER"
        assert summary["ok"] is True
        assert summary["failures"] == []

    def test_gate_p31_0_dependency(self):
        _, summary = p31_1_gate.run_gate()
        assert summary["p31_0_green"] is True

    def test_gate_fixtures_consumed(self):
        _, summary = p31_1_gate.run_gate()
        assert summary["fixtures_consumed"] is True
        assert summary["results_produced"] is True

    def test_gate_replay_deterministic(self):
        _, summary = p31_1_gate.run_gate()
        assert summary["replay_deterministic"] is True

    def test_gate_phase19_yellow(self):
        _, summary = p31_1_gate.run_gate()
        assert summary["phase19_yellow_preserved"] is True

    def test_gate_phase24_infra(self):
        _, summary = p31_1_gate.run_gate()
        assert summary["phase24_infrastructure_only_preserved"] is True


# --- Task family matrix ------------------------------------------------------

class TestTaskFamilyMatrix:
    def test_all_families_in_matrix(self):
        for family in TASK_FAMILIES:
            assert family in TASK_FAMILY_MATRIX

    def test_get_family_spec(self):
        spec = get_family_spec("code_generation")
        assert spec["family_id"] == "code_generation"
        assert "evaluation_method" in spec

    def test_get_family_spec_unknown(self):
        from hg_runtime.evaluation_harness.schemas import EvaluationHarnessBoundaryError
        with pytest.raises(EvaluationHarnessBoundaryError):
            get_family_spec("agi_mastery")


# --- Coverage ----------------------------------------------------------------

class TestCoverage:
    def test_full_coverage(self):
        cov = get_coverage(list(TASK_FAMILIES))
        assert cov["coverage_ratio"] == 1.0
        assert cov["uncovered"] == []

    def test_partial_coverage(self):
        cov = get_coverage(["code_generation"])
        assert cov["coverage_ratio"] < 1.0
        assert "code_generation" in cov["covered"]
        assert len(cov["uncovered"]) > 0

    def test_unknown_families(self):
        cov = get_coverage(["code_generation", "agi_mastery"])
        assert "agi_mastery" in cov["unknown"]

    def test_coverage_not_competence(self):
        cov = get_coverage(list(TASK_FAMILIES))
        assert cov["coverage_is_not_competence"] is True


# --- Fixture evaluation ------------------------------------------------------

class TestFixtureEvaluation:
    def test_pass_when_match(self):
        fixture = builtin_fixtures()[0]
        observed = dict(fixture["expected_output"])
        result = evaluate_fixture(fixture, observed, "test_model")
        assert result["state"] == "PASS"

    def test_fail_when_mismatch(self):
        fixture = builtin_fixtures()[0]
        observed = {"contains_def": False, "returns_sum": True}
        result = evaluate_fixture(fixture, observed, "test_model")
        assert result["state"] == "FAIL"

    def test_result_contains_eo(self):
        fixture = builtin_fixtures()[0]
        observed = dict(fixture["expected_output"])
        result = evaluate_fixture(fixture, observed, "test_model")
        assert "expected_observed" in result
        assert "result" in result


# --- Run fixtures ------------------------------------------------------------

class TestRunFixtures:
    def test_all_pass(self):
        fixtures = builtin_fixtures()
        observed = {f["task_id"]: dict(f["expected_output"]) for f in fixtures}
        summary = run_fixtures(fixtures, observed, "test_model")
        assert summary["passed"] == len(fixtures)
        assert summary["failed"] == 0

    def test_defer_missing(self):
        fixtures = builtin_fixtures()
        summary = run_fixtures(fixtures, {}, "test_model")
        assert summary["deferred"] == len(fixtures)

    def test_score_not_truth(self):
        fixtures = builtin_fixtures()
        observed = {f["task_id"]: dict(f["expected_output"]) for f in fixtures}
        summary = run_fixtures(fixtures, observed, "test_model")
        assert summary["score_is_not_truth"] is True
        assert summary["score_is_not_competence"] is True

    def test_coverage_recorded(self):
        fixtures = builtin_fixtures()
        observed = {f["task_id"]: dict(f["expected_output"]) for f in fixtures}
        summary = run_fixtures(fixtures, observed, "test_model")
        assert "coverage" in summary
        assert summary["coverage"]["coverage_ratio"] > 0


# --- Replay ------------------------------------------------------------------

class TestReplay:
    def test_deterministic_replay(self):
        fixtures = builtin_fixtures()
        observed = {f["task_id"]: dict(f["expected_output"]) for f in fixtures}
        replay = replay_evaluation(fixtures, observed, "test_model", iterations=3)
        assert replay["deterministic"] is True
        assert replay["unique_hashes"] == 1
        assert replay["iterations"] == 3

    def test_replay_not_truth(self):
        fixtures = builtin_fixtures()
        observed = {f["task_id"]: dict(f["expected_output"]) for f in fixtures}
        replay = replay_evaluation(fixtures, observed, "test_model", iterations=2)
        assert replay["replay_is_not_truth"] is True


# --- Artifact writer ---------------------------------------------------------

class TestArtifactWriter:
    def test_writes_artifacts(self, tmp_path):
        fixtures = builtin_fixtures()
        observed = {f["task_id"]: dict(f["expected_output"]) for f in fixtures}
        summary = run_fixtures(fixtures, observed, "test_model")
        write_evaluation_artifacts(tmp_path / "proof", summary, fixtures)
        assert (tmp_path / "proof" / "evaluation_summary.json").exists()
        assert (tmp_path / "proof" / "coverage.json").exists()
        assert (tmp_path / "proof" / "results.jsonl").exists()
        assert (tmp_path / "proof" / "fixtures_index.json").exists()


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p31_0_green": True,
            "fixtures_consumed": True,
            "results_produced": True,
            "task_family_coverage_recorded": True,
            "gaps_recorded": True,
            "score_not_truth": True,
            "family_not_general_competence": True,
            "no_live_providers": True,
            "no_web": True,
            "no_tool_authorization": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "replay_deterministic": True,
            "secret_redaction_passed": True,
            "proof_bundle_valid": True,
            "report_present": True,
        }
        data.update(overrides)
        return data

    def test_valid_passes(self):
        result = validate_p31_1_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p31_0_fails(self):
        result = validate_p31_1_gate(self._summary(p31_0_green=False))
        assert result["ok"] is False
        assert "p31_0_required" in result["failures"]

    def test_not_deterministic_fails(self):
        result = validate_p31_1_gate(self._summary(replay_deterministic=False))
        assert result["ok"] is False
