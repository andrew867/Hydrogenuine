"""DTX safe text document exchange consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_dtx_consolidation_gate.py"

_spec = importlib.util.spec_from_file_location("dtx_consolidation_gate", _GATE_PATH)
dtx_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dtx_gate)


def _consolidation():
    return dtx_gate.build_consolidation()


def test_dtx_consolidation_aggregates_dtx_0_through_4():
    ids = {p["phase"] for p in _consolidation()["phase_index"]}
    for i in range(5):
        assert f"DTX-{i}" in ids


def test_dtx_consolidation_integrates_dib_and_upstream_layers():
    integrations = {item["integration"] for item in _consolidation()["integration_index"]}
    assert "DIB-DOCUMENT-INTAKE-BOUNDARY-CONSOLIDATION" in integrations
    assert "LEB-LOCAL-EVIDENCE-BRIDGE-CONSOLIDATION" in integrations


def test_dtx_consolidation_boundaries_enforced():
    b = _consolidation()["boundary_matrix"]
    assert b["safe_text_markdown_only"] is True
    assert b["pdf_disabled"] is True
    assert b["ocr_disabled"] is True
    assert b["no_adapter_as_promotion"] is True


def test_dtx_consolidation_phase_links_present():
    for phase in _consolidation()["phase_index"]:
        assert phase["test"]
        assert phase["gate"]
        assert phase["report"]
