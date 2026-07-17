"""DIB document intake boundary consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_dib_consolidation_gate.py"

_spec = importlib.util.spec_from_file_location("dib_consolidation_gate", _GATE_PATH)
dib_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dib_gate)


def _consolidation():
    return dib_gate.build_consolidation()


def test_dib_consolidation_aggregates_dib_0_through_5():
    ids = {p["phase"] for p in _consolidation()["phase_index"]}
    for i in range(6):
        assert f"DIB-{i}" in ids


def test_dib_consolidation_integrates_upstream_layers():
    integrations = {item["integration"] for item in _consolidation()["integration_index"]}
    assert "OES-OPERATOR-EVIDENCE-SOAK-CONSOLIDATION" in integrations
    assert "OEC-OPERATOR-EVIDENCE-CORPUS-CONSOLIDATION" in integrations
    assert "EWP-EVIDENCE-WORKBENCH-PACKET-CONSOLIDATION" in integrations
    assert "SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION" in integrations
    assert "LEB-LOCAL-EVIDENCE-BRIDGE-CONSOLIDATION" in integrations


def test_dib_consolidation_boundaries_enforced():
    b = _consolidation()["boundary_matrix"]
    assert b["safe_text_markdown_extraction_only"] is True
    assert b["pdf_disabled"] is True
    assert b["ocr_disabled"] is True
    assert b["no_arbitrary_ingestion"] is True
    assert b["no_document_as_truth"] is True


def test_dib_consolidation_phase_links_present():
    for phase in _consolidation()["phase_index"]:
        assert phase["test"]
        assert phase["gate"]
        assert phase["report"]
