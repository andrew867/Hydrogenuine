"""Safe Local Evidence Alpha consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_safe_local_evidence_alpha_gate.py"

_spec = importlib.util.spec_from_file_location("safe_local_evidence_alpha_gate", _GATE_PATH)
alpha_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(alpha_gate)


def _alpha():
    return alpha_gate.build_alpha()


# --- Chain coverage --------------------------------------------------------

def test_alpha_aggregates_full_chain():
    phases = _alpha()["phase_index"]
    assert len(phases) == 18
    groups = {p["group"] for p in phases}
    assert groups == {"WMBR", "AIS", "LEB"}


def test_alpha_all_phases_green():
    for p in _alpha()["phase_index"]:
        assert p["is_green"], f"{p['phase']} not green: {p['gate_verdict']}"


def test_alpha_includes_leb_0_through_7():
    ids = {p["phase"] for p in _alpha()["phase_index"]}
    for i in range(8):
        assert f"LEB-{i}" in ids
    assert "LEB-CONSOLIDATION" in ids


def test_alpha_includes_wmbr_and_ais():
    ids = {p["phase"] for p in _alpha()["phase_index"]}
    assert {"WMBR-04", "WMBR-05", "WMBR-06", "WMBR-TRANCHE"} <= ids
    assert {"AIS-1", "AIS-2", "AIS-3", "AIS-6", "AIS-7"} <= ids


def test_alpha_each_phase_has_proof_bundle():
    for p in _alpha()["phase_index"]:
        assert p["proof_bundle"], f"{p['phase']} missing proof bundle"


# --- Boundaries ------------------------------------------------------------

def test_alpha_boundaries_enforced():
    b = _alpha()["boundary_matrix"]
    assert b["no_live_web"] is True
    assert b["no_external_providers"] is True
    assert b["no_arbitrary_file_ingestion"] is True
    assert b["no_pdf_ocr"] is True
    assert b["no_truth_claim"] is True
    assert b["no_authority"] is True
    assert b["no_automatic_belief_promotion"] is True
    assert b["no_patch_application"] is True
    assert b["no_deletion"] is True
    assert b["operator_inbox_disabled_by_default"] is True


def test_alpha_preserves_phase19_yellow():
    assert _alpha()["boundary_matrix"]["phase19_yellow_preserved"] is True


def test_alpha_preserves_phase24_infrastructure_only():
    assert _alpha()["boundary_matrix"]["phase24_infrastructure_only_preserved"] is True


def test_alpha_does_not_complete_wmbr01_parent():
    assert _alpha()["boundary_matrix"]["wmbr01_parent_not_completed"] is True


# --- Gate run --------------------------------------------------------------

def test_alpha_gate_run_is_green():
    code, summary = alpha_gate.run_gate()
    assert code == 0
    assert summary["verdict"] == "GREEN_SAFE_LOCAL_EVIDENCE_ALPHA"
    assert summary["ok"] is True
    assert summary["failures"] == []
    assert summary["green_phase_count"] == summary["phase_count"] == 18


def test_alpha_chain_summary_doctrine():
    cs = _alpha()["chain_summary"]
    assert cs["bridge_may_not_browse_the_world"] is True
    assert cs["bridge_may_not_believe_without_review"] is True
    assert cs["bridge_may_not_act"] is True
