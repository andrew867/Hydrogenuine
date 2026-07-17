"""OES operator evidence soak consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_oes_consolidation_gate.py"

_spec = importlib.util.spec_from_file_location("oes_consolidation_gate", _GATE_PATH)
oes_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oes_gate)


def _consolidation():
    return oes_gate.build_consolidation()


def test_oes_consolidation_aggregates_oes_0_through_3():
    ids = {p["phase"] for p in _consolidation()["phase_index"]}
    for i in range(4):
        assert f"OES-{i}" in ids


def test_oes_consolidation_integrates_oec_ewp_sqp_ais():
    integrations = {item["integration"] for item in _consolidation()["integration_index"]}
    assert "OEC-OPERATOR-EVIDENCE-CORPUS-CONSOLIDATION" in integrations
    assert "EWP-EVIDENCE-WORKBENCH-PACKET-CONSOLIDATION" in integrations
    assert "SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION" in integrations


def test_oes_consolidation_boundaries_enforced():
    b = _consolidation()["boundary_matrix"]
    assert b["no_soak_as_truth"] is True
    assert b["no_replay_match_as_truth"] is True
    assert b["no_mutation_auto_repair"] is True
    assert b["no_arbitrary_ingestion"] is True
    assert b["no_pdf_ocr"] is True


def test_oes_consolidation_next_safe_steps_present():
    assert _consolidation()["chain_summary"]["next_safe_steps"]
