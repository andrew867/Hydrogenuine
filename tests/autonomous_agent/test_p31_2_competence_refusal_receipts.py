"""P31-2 competence refusal and regression receipts tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p31_2_competence_refusal_gate.py"
_spec = importlib.util.spec_from_file_location("p31_2_gate", _GATE_PATH)
p31_2_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p31_2_gate)

from hg_runtime.evaluation_harness.schemas import COMPETENCE_CLAIM_TYPES
from hg_runtime.evaluation_harness.competence_refusal import (
    generate_all_refusals,
    check_all_claim_types_covered,
)
from hg_runtime.evaluation_harness.regression_receipts import create_evaluation_receipt
from hg_runtime.evaluation_harness.evaluation_boundary_matrix import (
    MUST_BE_FALSE,
    MUST_BE_TRUE,
    check_boundary_matrix,
)
from hg_runtime.evaluation_harness.evaluation_receipt_writer import write_receipt_artifacts
from hg_runtime.evaluation_harness.gate import validate_p31_2_gate


# --- Gate run ----------------------------------------------------------------

class TestP31_2GateRun:
    def test_gate_green(self):
        code, summary = p31_2_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P31_2_COMPETENCE_REFUSAL_RECEIPTS"
        assert summary["ok"] is True
        assert summary["failures"] == []

    def test_gate_p31_1_dependency(self):
        _, summary = p31_2_gate.run_gate()
        assert summary["p31_1_green"] is True

    def test_gate_all_claims_covered(self):
        _, summary = p31_2_gate.run_gate()
        assert summary["all_claim_types_covered"] is True

    def test_gate_phase19_yellow(self):
        _, summary = p31_2_gate.run_gate()
        assert summary["phase19_yellow_preserved"] is True


# --- Competence refusal engine -----------------------------------------------

class TestCompetenceRefusal:
    def test_generate_all(self):
        refusals = generate_all_refusals("test_model")
        assert len(refusals) == len(COMPETENCE_CLAIM_TYPES)

    def test_all_refused(self):
        for r in generate_all_refusals("test_model"):
            assert r["refused"] is True
            assert r["schema"] == "competence_claim_refusal_v1"

    def test_coverage_complete(self):
        refusals = generate_all_refusals("test_model")
        coverage = check_all_claim_types_covered(refusals)
        assert coverage["all_covered"] is True
        assert coverage["missing"] == []

    def test_coverage_partial(self):
        refusals = generate_all_refusals("test_model")[:3]
        coverage = check_all_claim_types_covered(refusals)
        assert coverage["all_covered"] is False
        assert len(coverage["missing"]) > 0

    def test_each_claim_type(self):
        for ct in sorted(COMPETENCE_CLAIM_TYPES):
            refusals = generate_all_refusals("test_model")
            covered = {r["claim_type"] for r in refusals}
            assert ct in covered, f"claim type not covered: {ct}"


# --- Regression receipts -----------------------------------------------------

class TestRegressionReceipts:
    def test_create_receipt(self):
        r = create_evaluation_receipt(
            run_id="test-run-1",
            model_id="test_model",
            task_count=10,
            passed=8,
            failed=2,
        )
        assert r["schema"] == "evaluation_receipt_v1"
        assert r["receipt_is_not_deployment_permission"] is True
        assert r["receipt_is_not_competence"] is True
        assert "receipt_hash" in r

    def test_receipt_with_boundary_violations(self):
        r = create_evaluation_receipt(
            run_id="test-run-2",
            model_id="test_model",
            task_count=5,
            passed=3,
            failed=1,
            refused_correctly=1,
            boundary_violations=0,
        )
        assert r["boundary_violations"] == 0


# --- Boundary matrix ---------------------------------------------------------

class TestBoundaryMatrix:
    def test_clean_record_passes(self):
        record = {k: True for k in MUST_BE_TRUE}
        record.update({k: False for k in MUST_BE_FALSE})
        result = check_boundary_matrix(record)
        assert result["ok"] is True

    def test_missing_true_fails(self):
        record = {k: True for k in MUST_BE_TRUE}
        record.update({k: False for k in MUST_BE_FALSE})
        record["evaluation_is_not_truth"] = False
        result = check_boundary_matrix(record)
        assert result["ok"] is False

    def test_forbidden_set_fails(self):
        record = {k: True for k in MUST_BE_TRUE}
        record.update({k: False for k in MUST_BE_FALSE})
        record["competence_claimed"] = True
        result = check_boundary_matrix(record)
        assert result["ok"] is False


# --- Receipt writer ----------------------------------------------------------

class TestReceiptWriter:
    def test_writes_artifacts(self, tmp_path):
        receipt = create_evaluation_receipt(
            run_id="wr-1", model_id="m1", task_count=5, passed=5, failed=0,
        )
        refusals = generate_all_refusals("m1")
        boundary = check_boundary_matrix({k: True for k in MUST_BE_TRUE})
        write_receipt_artifacts(tmp_path / "proof", [receipt], refusals, boundary)
        assert (tmp_path / "proof" / "receipts.jsonl").exists()
        assert (tmp_path / "proof" / "refusals.jsonl").exists()
        assert (tmp_path / "proof" / "boundary_check.json").exists()
        assert (tmp_path / "proof" / "refusal_coverage.json").exists()


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p31_1_green": True,
            "refusals_produced": True,
            "all_claim_types_covered": True,
            "receipts_produced": True,
            "evaluation_is_not_truth": True,
            "evaluation_is_not_competence": True,
            "no_live_effects": True,
            "no_web_provider": True,
            "no_pdf_ocr_html": True,
            "no_tool_authorization": True,
            "no_automatic_belief_promotion": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "secret_redaction_passed": True,
            "proof_bundle_valid": True,
            "report_present": True,
        }
        data.update(overrides)
        return data

    def test_valid_passes(self):
        result = validate_p31_2_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p31_1_fails(self):
        result = validate_p31_2_gate(self._summary(p31_1_green=False))
        assert result["ok"] is False

    def test_missing_refusals_fails(self):
        result = validate_p31_2_gate(self._summary(refusals_produced=False))
        assert result["ok"] is False
