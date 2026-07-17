"""P31-0 evaluation harness schema tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p31_0_evaluation_harness_schema_gate.py"
_spec = importlib.util.spec_from_file_location("p31_0_gate", _GATE_PATH)
p31_0_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p31_0_gate)

from hg_runtime.evaluation_harness.schemas import (
    COMPETENCE_CLAIM_TYPES,
    EVALUATION_RESULT_STATES,
    FORBIDDEN_TRUE,
    P31_INVARIANTS,
    PROVIDER_MODE,
    RECORD_TYPES,
    TASK_FAMILIES,
    EvaluationHarnessBoundaryError,
    assert_neutral,
    neutral_flags,
    record_hash,
)
from hg_runtime.evaluation_harness.evaluation_policy import create_evaluation_policy
from hg_runtime.evaluation_harness.task_family import create_task_family
from hg_runtime.evaluation_harness.evaluation_fixture import create_evaluation_fixture
from hg_runtime.evaluation_harness.expected_observed_record import create_expected_observed_record
from hg_runtime.evaluation_harness.evaluation_result import create_evaluation_result
from hg_runtime.evaluation_harness.competence_claim_refusal import (
    create_competence_claim_refusal,
    refuse_if_competence_claim,
)
from hg_runtime.evaluation_harness.fixtures import builtin_fixtures
from hg_runtime.evaluation_harness.gate import validate_p31_0_gate
from hg_runtime.evaluation_harness.hashing import stable_hash, with_hash
from hg_runtime.evaluation_harness.redaction import secret_scan


# --- Gate run ----------------------------------------------------------------

class TestP31_0GateRun:
    def test_gate_green(self):
        code, summary = p31_0_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P31_0_EVALUATION_HARNESS_SCHEMAS"
        assert summary["ok"] is True
        assert summary["failures"] == []

    def test_gate_schema_coverage(self):
        _, summary = p31_0_gate.run_gate()
        assert summary["record_types_count"] == len(RECORD_TYPES)
        assert summary["task_families_count"] == len(TASK_FAMILIES)
        assert summary["invariants_count"] == len(P31_INVARIANTS)

    def test_gate_replay_deterministic(self):
        _, summary = p31_0_gate.run_gate()
        assert summary["replay_deterministic"] is True

    def test_gate_phase19_yellow(self):
        _, summary = p31_0_gate.run_gate()
        assert summary["phase19_yellow_preserved"] is True

    def test_gate_phase24_infra(self):
        _, summary = p31_0_gate.run_gate()
        assert summary["phase24_infrastructure_only_preserved"] is True

    def test_gate_no_forbidden_flags(self):
        _, summary = p31_0_gate.run_gate()
        for key in FORBIDDEN_TRUE:
            assert summary.get(key) is not True or key not in summary, f"forbidden flag set: {key}"


# --- Schema constants --------------------------------------------------------

class TestSchemaConstants:
    def test_record_types_complete(self):
        expected = {
            "evaluation_policy_v1", "task_family_v1", "evaluation_fixture_v1",
            "expected_observed_record_v1", "evaluation_result_v1",
            "competence_claim_refusal_v1", "evaluation_harness_gate_result_v1",
        }
        assert RECORD_TYPES == expected

    def test_task_families(self):
        assert len(TASK_FAMILIES) >= 4
        assert "code_generation" in TASK_FAMILIES
        assert "boundary_enforcement" in TASK_FAMILIES

    def test_result_states(self):
        assert EVALUATION_RESULT_STATES == {"PASS", "FAIL", "DEFER", "REFUSE"}

    def test_invariants_count(self):
        assert len(P31_INVARIANTS) == 12

    def test_provider_mode(self):
        assert PROVIDER_MODE == "FIXTURE_ONLY_LOCAL_ONLY"

    def test_competence_claim_types(self):
        assert len(COMPETENCE_CLAIM_TYPES) == 8
        assert "evaluation_pass_treated_as_truth" in COMPETENCE_CLAIM_TYPES


# --- Evaluation policy -------------------------------------------------------

class TestEvaluationPolicy:
    def test_create_default(self):
        policy = create_evaluation_policy()
        assert policy["schema"] == "evaluation_policy_v1"
        assert policy["evaluation_is_not_truth"] is True
        assert policy["evaluation_is_not_competence"] is True
        assert "policy_hash" in policy

    def test_reject_non_fixture_provider(self):
        with pytest.raises(EvaluationHarnessBoundaryError, match="provider_mode_must_be_fixture_only"):
            create_evaluation_policy(provider_mode="live")

    def test_reject_non_local_source(self):
        with pytest.raises(EvaluationHarnessBoundaryError, match="fixture_source_must_be_local_only"):
            create_evaluation_policy(fixture_source="web")

    def test_reject_unknown_family(self):
        with pytest.raises(EvaluationHarnessBoundaryError, match="unknown_task_families"):
            create_evaluation_policy(task_families=frozenset({"agi_test"}))


# --- Task family -------------------------------------------------------------

class TestTaskFamily:
    def test_create_valid(self):
        tf = create_task_family(family_id="code_generation", description="Generate code")
        assert tf["schema"] == "task_family_v1"
        assert tf["family_is_not_general_competence"] is True

    def test_reject_unknown(self):
        with pytest.raises(EvaluationHarnessBoundaryError, match="unknown_task_family"):
            create_task_family(family_id="agi_mastery", description="bad")


# --- Evaluation fixture ------------------------------------------------------

class TestEvaluationFixture:
    def test_create_valid(self):
        fixture = create_evaluation_fixture(
            task_family="classification",
            task_id="test-1",
            input_data={"text": "hello"},
            expected_output={"category": "greeting"},
        )
        assert fixture["schema"] == "evaluation_fixture_v1"
        assert fixture["fixture_is_not_truth"] is True
        assert "fixture_hash" in fixture

    def test_reject_unknown_family(self):
        with pytest.raises(EvaluationHarnessBoundaryError):
            create_evaluation_fixture(
                task_family="nonexistent",
                task_id="bad",
                input_data={},
                expected_output={},
            )


# --- Expected/observed record ------------------------------------------------

class TestExpectedObservedRecord:
    def test_all_match(self):
        eo = create_expected_observed_record(
            task_id="t1", model_id="m1",
            expected_output={"a": 1}, observed_output={"a": 1},
            expected_properties=["a"],
        )
        assert eo["properties_matched"] == ["a"]
        assert eo["properties_failed"] == []
        assert eo["match_is_not_truth"] is True

    def test_property_mismatch(self):
        eo = create_expected_observed_record(
            task_id="t1", model_id="m1",
            expected_output={"a": 1}, observed_output={"a": 2},
            expected_properties=["a"],
        )
        assert eo["properties_failed"] == ["a"]


# --- Evaluation result -------------------------------------------------------

class TestEvaluationResult:
    def test_create_pass(self):
        r = create_evaluation_result(
            task_id="t1", task_family="code_generation",
            model_id="m1", state="PASS",
        )
        assert r["schema"] == "evaluation_result_v1"
        assert r["evaluation_is_not_competence"] is True

    def test_reject_unknown_state(self):
        with pytest.raises(EvaluationHarnessBoundaryError, match="unknown_result_state"):
            create_evaluation_result(
                task_id="t1", task_family="code_generation",
                model_id="m1", state="DEPLOY",
            )


# --- Competence claim refusal ------------------------------------------------

class TestCompetenceClaimRefusal:
    def test_create_refusal(self):
        r = create_competence_claim_refusal(
            model_id="m1",
            claim_type="evaluation_pass_treated_as_truth",
            reason="not truth",
        )
        assert r["schema"] == "competence_claim_refusal_v1"
        assert r["refused"] is True
        assert "refusal_hash" in r

    def test_reject_unknown_claim(self):
        with pytest.raises(EvaluationHarnessBoundaryError, match="unknown_claim_type"):
            create_competence_claim_refusal(
                model_id="m1", claim_type="agi_achieved",
            )

    def test_refuse_if_claim_present(self):
        record = {"model_id": "m1", "evaluation_pass_treated_as_truth": True}
        refusal = refuse_if_competence_claim(record)
        assert refusal is not None
        assert refusal["refused"] is True

    def test_no_refusal_if_clean(self):
        record = {"model_id": "m1"}
        assert refuse_if_competence_claim(record) is None


# --- Fixtures ----------------------------------------------------------------

class TestBuiltinFixtures:
    def test_fixture_count(self):
        fixtures = builtin_fixtures()
        assert len(fixtures) >= 6

    def test_all_valid_families(self):
        for f in builtin_fixtures():
            assert f["task_family"] in TASK_FAMILIES

    def test_all_have_hashes(self):
        for f in builtin_fixtures():
            assert "fixture_hash" in f


# --- Hashing -----------------------------------------------------------------

class TestHashing:
    def test_deterministic(self):
        r = {"a": 1, "b": 2}
        assert stable_hash(r) == stable_hash(r)

    def test_excludes_hash_fields(self):
        r1 = {"a": 1, "record_hash": "x"}
        r2 = {"a": 1, "record_hash": "y"}
        assert stable_hash(r1) == stable_hash(r2)

    def test_with_hash(self):
        r = {"a": 1}
        result = with_hash(r)
        assert "record_hash" in result


# --- Redaction ---------------------------------------------------------------

class TestRedaction:
    def test_clean_passes(self):
        assert secret_scan({"hello": "world"}) is True

    def test_secret_detected(self):
        assert secret_scan({"key": "sk_live_abc123"}) is False


# --- Boundary enforcement ----------------------------------------------------

class TestBoundaryEnforcement:
    def test_neutral_flags_all_false(self):
        flags = neutral_flags()
        for k, v in flags.items():
            assert v is False, f"neutral flag not false: {k}"

    def test_assert_neutral_passes(self):
        assert_neutral(neutral_flags())

    def test_assert_neutral_rejects(self):
        bad = neutral_flags()
        bad["evaluation_treated_as_truth"] = True
        with pytest.raises(EvaluationHarnessBoundaryError, match="forbidden_true"):
            assert_neutral(bad)

    def test_assert_neutral_recursive(self):
        bad = {"nested": {"evaluation_treated_as_truth": True}}
        with pytest.raises(EvaluationHarnessBoundaryError):
            assert_neutral(bad)


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "policy_written": True,
            "fixtures_written": True,
            "task_families_written": True,
            "expected_observed_written": True,
            "result_written": True,
            "refusal_written": True,
            "evaluation_is_not_truth": True,
            "evaluation_is_not_competence": True,
            "benchmark_is_not_deployment_permission": True,
            "no_tool_authorization": True,
            "no_live_effects": True,
            "no_web_provider": True,
            "no_pdf_ocr_html": True,
            "no_automatic_belief_promotion": True,
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
        result = validate_p31_0_gate(self._summary())
        assert result["ok"] is True

    def test_missing_policy_fails(self):
        result = validate_p31_0_gate(self._summary(policy_written=False))
        assert result["ok"] is False
        assert "policy_required" in result["failures"]

    def test_forbidden_flag_fails(self):
        result = validate_p31_0_gate(self._summary(evaluation_treated_as_truth=True))
        assert result["ok"] is False

    def test_phase19_not_preserved_fails(self):
        result = validate_p31_0_gate(self._summary(phase19_yellow_preserved=False))
        assert result["ok"] is False
        assert "phase19_not_yellow" in result["failures"]
