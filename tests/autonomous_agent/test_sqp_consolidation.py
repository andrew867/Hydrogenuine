"""SQP source quality provenance consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_sqp_consolidation_gate.py"

_spec = importlib.util.spec_from_file_location("sqp_consolidation_gate", _GATE_PATH)
sqp_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sqp_gate)


def _consolidation():
    return sqp_gate.build_consolidation()


# --- Chain coverage --------------------------------------------------------

def test_sqp_consolidation_aggregates_sqp_0_through_5():
    ids = {p["phase"] for p in _consolidation()["phase_index"]}
    for i in range(6):
        assert f"SQP-{i}" in ids


def test_sqp_consolidation_all_phases_green():
    for p in _consolidation()["phase_index"]:
        assert p["is_green"], f"{p['phase']} not green: {p['gate_verdict']}"


def test_sqp_consolidation_each_phase_has_proof_bundle():
    for p in _consolidation()["phase_index"]:
        assert p["proof_bundle"], f"{p['phase']} missing proof bundle"


# --- Integration -----------------------------------------------------------

def test_sqp_consolidation_integrates_reviewed_local_evidence_beta():
    b = _consolidation()["boundary_matrix"]
    assert b["reviewed_local_evidence_beta_green"] is True


# --- Boundaries ------------------------------------------------------------

def test_sqp_consolidation_boundaries_enforced():
    b = _consolidation()["boundary_matrix"]
    assert b["no_live_web"] is True
    assert b["no_external_providers"] is True
    assert b["no_arbitrary_file_ingestion"] is True
    assert b["no_pdf_ocr"] is True
    assert b["no_truth_claim"] is True
    assert b["no_authority"] is True
    assert b["no_duplicate_as_corroboration"] is True
    assert b["no_provenance_as_authority"] is True
    assert b["no_conflict_as_truth_resolution"] is True
    assert b["no_review_hint_as_approval"] is True
    assert b["no_automatic_belief_promotion"] is True
    assert b["no_deletion"] is True


def test_sqp_consolidation_preserves_phase19_and_phase24():
    b = _consolidation()["boundary_matrix"]
    assert b["phase19_yellow_preserved"] is True
    assert b["phase24_infrastructure_only_preserved"] is True


def test_sqp_consolidation_zero_is_not_agi():
    assert _consolidation()["boundary_matrix"]["zero_is_not_agi"] is True


def test_sqp_consolidation_chain_summary_doctrine():
    cs = _consolidation()["chain_summary"]
    assert cs["system_may_model_provenance"] is True
    assert cs["system_may_not_decide_truth"] is True
    assert cs["system_may_not_act"] is True


# --- Gate run --------------------------------------------------------------

def test_sqp_consolidation_gate_run_is_green():
    code, summary = sqp_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_SQP_SOURCE_QUALITY_PROVENANCE_CONSOLIDATION"
    assert summary["ok"] is True
    assert summary["failures"] == []
    assert summary["green_phase_count"] == summary["phase_count"] == 6
