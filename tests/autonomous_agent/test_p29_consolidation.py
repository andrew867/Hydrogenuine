"""P29 tool-mediated workbench consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p29_consolidation_gate.py"
_spec = importlib.util.spec_from_file_location("p29_consolidation_gate", _GATE_PATH)
p29_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p29_gate)

from hg_runtime.tool_mediated_workbench.schemas import PHASE19_VERDICT, PHASE24_STATUS
from hg_runtime.tool_mediated_workbench.workbench_gate import validate_p29_consolidation_gate


# --- Gate run ----------------------------------------------------------------

def test_p29_consolidation_gate_green():
    code, summary = p29_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_P29_TOOL_MEDIATED_WORKBENCH_CONSOLIDATION"
    assert summary["ok"] is True
    assert summary["failures"] == []


def test_p29_all_phases_green():
    _, summary = p29_gate.run_gate()
    assert summary["p29_0_green"] is True
    assert summary["p29_1_green"] is True
    assert summary["p29_2_green"] is True
    assert summary["p29_3_green"] is True
    assert summary["all_p29_phases_green"] is True


def test_p29_dependencies_green():
    _, summary = p29_gate.run_gate()
    assert summary["p26_green"] is True
    assert summary["p27_green"] is True
    assert summary["p28_green"] is True


def test_p29_tool_plan_not_permission():
    _, summary = p29_gate.run_gate()
    assert summary["tool_plan_not_permission"] is True
    assert summary["tool_plan_treated_as_permission"] is False


def test_p29_no_tool_authorization():
    _, summary = p29_gate.run_gate()
    assert summary["no_tool_authorization"] is True
    assert summary["tool_authorization_granted"] is False
    assert summary["tools_authorized"] is False


def test_p29_no_live_effects():
    _, summary = p29_gate.run_gate()
    assert summary["no_live_effects"] is True
    assert summary["live_external_side_effects_created"] is False


def test_p29_phase19_and_24_preserved():
    _, summary = p29_gate.run_gate()
    assert summary["phase19_yellow_preserved"] is True
    assert summary["phase24_infrastructure_only_preserved"] is True


# --- Gate validator ----------------------------------------------------------

def _summary(**overrides):
    data = {
        "p29_0_green": True, "p29_1_green": True,
        "p29_2_green": True, "p29_3_green": True,
        "p26_green": True, "p27_green": True, "p28_green": True,
        "tool_plan_not_permission": True,
        "tool_request_not_execution": True,
        "sandbox_not_live": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "no_web_provider": True,
        "no_patch_application": True,
        "no_deletion": True,
        "no_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_validator_passes():
    assert validate_p29_consolidation_gate(_summary())["ok"] is True


def test_validator_refuses_missing_p29_0():
    assert validate_p29_consolidation_gate(_summary(p29_0_green=False))["ok"] is False


def test_validator_refuses_missing_p26():
    assert validate_p29_consolidation_gate(_summary(p26_green=False))["ok"] is False


def test_validator_refuses_tool_authorization():
    assert validate_p29_consolidation_gate(_summary(tool_authorization_granted=True))["ok"] is False
