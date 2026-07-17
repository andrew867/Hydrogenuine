"""Generalist Runtime Batch B (P29+P30) consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_generalist_runtime_batch_b_p29_p30_gate.py"
_spec = importlib.util.spec_from_file_location("batch_b_gate", _GATE_PATH)
batch_b_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(batch_b_gate)


# --- Gate run ----------------------------------------------------------------

def test_batch_b_gate_green():
    code, summary = batch_b_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_GENERALIST_RUNTIME_BATCH_B_P29_P30"
    assert summary["ok"] is True
    assert summary["failures"] == []


def test_batch_b_p29_green():
    _, summary = batch_b_gate.run_gate()
    assert summary["p29_green"] is True


def test_batch_b_p30_green():
    _, summary = batch_b_gate.run_gate()
    assert summary["p30_green"] is True


def test_batch_b_dependencies_green():
    _, summary = batch_b_gate.run_gate()
    assert summary["p26_green"] is True
    assert summary["p27_green"] is True
    assert summary["p28_green"] is True
    assert summary["batch_a_green"] is True


def test_batch_b_tool_plan_not_permission():
    _, summary = batch_b_gate.run_gate()
    assert summary["tool_plan_not_permission"] is True
    assert summary["tool_plan_treated_as_permission"] is False


def test_batch_b_acquired_claim_not_truth():
    _, summary = batch_b_gate.run_gate()
    assert summary["acquired_claim_not_truth"] is True
    assert summary["acquired_claim_treated_as_truth"] is False


def test_batch_b_no_live_effects():
    _, summary = batch_b_gate.run_gate()
    assert summary["no_live_effects"] is True
    assert summary["live_external_side_effects_created"] is False


def test_batch_b_phase19_and_24_preserved():
    _, summary = batch_b_gate.run_gate()
    assert summary["phase19_yellow_preserved"] is True
    assert summary["phase24_infrastructure_only_preserved"] is True


def test_batch_b_recommended_next():
    _, summary = batch_b_gate.run_gate()
    assert "Batch C" in summary["recommended_next"]
    assert "operator review" in summary["recommended_next"]


# --- Validator ---------------------------------------------------------------

def _summary(**overrides):
    data = {
        "p26_green": True, "p27_green": True,
        "p28_green": True, "batch_a_green": True,
        "p29_green": True, "p30_green": True,
        "tool_plan_not_permission": True,
        "tool_request_not_execution": True,
        "acquired_claim_not_truth": True,
        "acquisition_task_not_action": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "no_live_web": True,
        "no_external_provider": True,
        "no_arbitrary_ingestion": True,
        "no_pdf_ocr": True,
        "no_html": True,
        "no_auto_belief_promotion": True,
        "no_deletion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_validator_passes():
    assert batch_b_gate.validate_batch_b_gate(_summary())["ok"] is True


def test_validator_fails_missing_p29():
    assert batch_b_gate.validate_batch_b_gate(_summary(p29_green=False))["ok"] is False


def test_validator_fails_missing_p30():
    assert batch_b_gate.validate_batch_b_gate(_summary(p30_green=False))["ok"] is False


def test_validator_fails_tool_permission():
    assert batch_b_gate.validate_batch_b_gate(_summary(tool_plan_treated_as_permission=True))["ok"] is False


def test_validator_fails_truth_claim():
    assert batch_b_gate.validate_batch_b_gate(_summary(acquired_claim_treated_as_truth=True))["ok"] is False
