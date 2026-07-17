"""Post-SLE-RC next-work consolidation handoff tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_post_sle_rc_next_work_handoff_gate.py"

_spec = importlib.util.spec_from_file_location("post_sle_rc_handoff_gate", _GATE_PATH)
handoff_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(handoff_gate)


def _handoff():
    return handoff_gate.build_handoff()


# --- Chain -----------------------------------------------------------------

def test_handoff_aggregates_all_four_phases():
    ids = {p["phase"] for p in _handoff()["phase_index"]}
    assert ids == {"SLE-RC", "SLE-RC-EXTENDED", "PHASE-25", "P26-GAP"}


def test_handoff_all_phases_green():
    for p in _handoff()["phase_index"]:
        assert p["is_green"], f"{p['phase']} not green: {p['gate_verdict']}"


def test_handoff_each_phase_has_proof():
    for p in _handoff()["phase_index"]:
        assert p["proof_bundle"], f"{p['phase']} missing proof bundle"


# --- Content ---------------------------------------------------------------

def test_handoff_p26_not_complete():
    assert _handoff()["p26_complete"] is False


def test_handoff_includes_next_lane_and_qa_and_forbidden():
    h = _handoff()
    assert h["next_recommended_lane"]
    assert h["monday_qa_plan"]
    assert h["forbidden_lanes"]


def test_handoff_boundary_assertions_enforced():
    b = _handoff()["boundary_assertions"]
    assert b["rc_not_deployment_permission"] is True
    assert b["rc_green_not_truth"] is True
    assert b["no_phase25_patch_applied"] is True
    assert b["no_p26_marked_complete_without_exact_gate"] is True
    assert b["no_automatic_belief_promotion"] is True


# --- Gate run --------------------------------------------------------------

def test_handoff_gate_run_is_green():
    code, summary = handoff_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_POST_SLE_RC_NEXT_WORK_HANDOFF"
    assert summary["ok"] is True
    assert summary["failures"] == []
    assert summary["green_phase_count"] == summary["phase_count"] == 4
    assert summary["phase19_yellow_preserved"] is True
    assert summary["phase24_infrastructure_only_preserved"] is True
    assert summary["p26_complete"] is False
