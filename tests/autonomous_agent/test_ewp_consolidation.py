"""EWP evidence workbench packet consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_ewp_consolidation_gate.py"

_spec = importlib.util.spec_from_file_location("ewp_consolidation_gate", _GATE_PATH)
ewp_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ewp_gate)


def _consolidation():
    return ewp_gate.build_consolidation()


def test_ewp_consolidation_aggregates_ewp_0_through_4():
    ids = {p["phase"] for p in _consolidation()["phase_index"]}
    for i in range(5):
        assert f"EWP-{i}" in ids


def test_ewp_consolidation_integrates_sqp_and_reviewed_beta():
    integrations = {item["integration"] for item in _consolidation()["integration_index"]}
    assert "SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION" in integrations
    assert "REVIEWED-LOCAL-EVIDENCE-BETA" in integrations


def test_ewp_consolidation_boundaries_enforced():
    b = _consolidation()["boundary_matrix"]
    assert b["no_truth_claim"] is True
    assert b["no_second_source_as_truth"] is True
    assert b["no_contradiction_as_resolution"] is True
    assert b["no_dashboard_as_approval"] is True
    assert b["no_automatic_belief_promotion"] is True


def test_ewp_consolidation_preserves_phase19_and_phase24():
    b = _consolidation()["boundary_matrix"]
    assert b["phase19_yellow_preserved"] is True
    assert b["phase24_infrastructure_only_preserved"] is True


def test_ewp_consolidation_chain_summary_doctrine():
    cs = _consolidation()["chain_summary"]
    assert cs["system_may_package_evidence"] is True
    assert cs["system_may_not_decide_truth"] is True
    assert cs["system_may_not_act"] is True
