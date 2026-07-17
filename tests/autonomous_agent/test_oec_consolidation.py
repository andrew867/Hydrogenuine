"""OEC operator evidence corpus consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_oec_consolidation_gate.py"

_spec = importlib.util.spec_from_file_location("oec_consolidation_gate", _GATE_PATH)
oec_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oec_gate)


def _consolidation():
    return oec_gate.build_consolidation()


def test_oec_consolidation_aggregates_oec_0_through_3():
    ids = {p["phase"] for p in _consolidation()["phase_index"]}
    for i in range(4):
        assert f"OEC-{i}" in ids


def test_oec_consolidation_integrates_ewp_and_sqp():
    integrations = {item["integration"] for item in _consolidation()["integration_index"]}
    assert "EWP-EVIDENCE-WORKBENCH-PACKET-CONSOLIDATION" in integrations
    assert "SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION" in integrations


def test_oec_consolidation_boundaries_enforced():
    b = _consolidation()["boundary_matrix"]
    assert b["no_corpus_as_truth"] is True
    assert b["no_expected_outcome_as_proof"] is True
    assert b["no_arbitrary_ingestion"] is True
    assert b["no_pdf_ocr"] is True


def test_oec_consolidation_fixture_families_listed():
    assert len(_consolidation()["chain_summary"]["corpus_fixture_families"]) == 10
