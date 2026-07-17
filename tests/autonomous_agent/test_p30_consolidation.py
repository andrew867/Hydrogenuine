"""P30 knowledge acquisition loop consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p30_consolidation_gate.py"
_spec = importlib.util.spec_from_file_location("p30_consolidation_gate", _GATE_PATH)
p30_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p30_gate)

from hg_runtime.knowledge_acquisition_loop.knowledge_gate import validate_p30_consolidation_gate


# --- Gate run ----------------------------------------------------------------

def test_p30_consolidation_gate_green():
    code, summary = p30_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_P30_KNOWLEDGE_ACQUISITION_LOOP_CONSOLIDATION"
    assert summary["ok"] is True
    assert summary["failures"] == []


def test_p30_all_phases_green():
    _, summary = p30_gate.run_gate()
    assert summary["p30_0_green"] is True
    assert summary["p30_1_green"] is True
    assert summary["p30_2_green"] is True
    assert summary["p30_3_green"] is True


def test_p30_dependencies_green():
    _, summary = p30_gate.run_gate()
    assert summary["p26_green"] is True
    assert summary["p27_green"] is True
    assert summary["p28_green"] is True
    assert summary["p29_green"] is True


def test_p30_acquired_claim_not_truth():
    _, summary = p30_gate.run_gate()
    assert summary["acquired_claim_not_truth"] is True
    assert summary["acquired_claim_treated_as_truth"] is False


def test_p30_no_live_effects():
    _, summary = p30_gate.run_gate()
    assert summary["no_live_effects"] is True
    assert summary["live_external_side_effects_created"] is False


def test_p30_phase19_and_24_preserved():
    _, summary = p30_gate.run_gate()
    assert summary["phase19_yellow_preserved"] is True
    assert summary["phase24_infrastructure_only_preserved"] is True


# --- Validator ---------------------------------------------------------------

def _summary(**overrides):
    data = {
        "p30_0_green": True, "p30_1_green": True,
        "p30_2_green": True, "p30_3_green": True,
        "p26_green": True, "p27_green": True,
        "p28_green": True, "p29_green": True,
        "acquired_claim_not_truth": True,
        "acquisition_result_not_belief": True,
        "source_not_authority": True,
        "task_not_action": True,
        "no_live_web": True, "no_external_provider": True,
        "no_arbitrary_ingestion": True, "no_pdf_ocr": True,
        "no_auto_belief_promotion": True,
        "no_live_effects": True, "no_deletion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True, "report_present": True,
    }
    data.update(overrides)
    return data


def test_validator_passes():
    assert validate_p30_consolidation_gate(_summary())["ok"] is True


def test_validator_refuses_missing_p30_0():
    assert validate_p30_consolidation_gate(_summary(p30_0_green=False))["ok"] is False


def test_validator_refuses_missing_p29():
    assert validate_p30_consolidation_gate(_summary(p29_green=False))["ok"] is False


def test_validator_refuses_truth_claim():
    assert validate_p30_consolidation_gate(_summary(acquired_claim_treated_as_truth=True))["ok"] is False
