"""SLE Safe Local Evidence Release Candidate consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_GATE_PATH = ROOT / "scripts/evals/autonomous_agent_sle_rc_consolidation_gate.py"

_spec = importlib.util.spec_from_file_location("sle_rc_consolidation_gate", _GATE_PATH)
sle_rc_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sle_rc_gate)


def _consolidation():
    return sle_rc_gate.build_consolidation()


def test_sle_rc_consolidation_aggregates_sle_rc_0_through_3():
    ids = {p["phase"] for p in _consolidation()["phase_index"]}
    for i in range(4):
        assert f"SLE-RC-{i}" in ids


def test_sle_rc_consolidation_links_all_component_families():
    families = {row["component_family"] for row in _consolidation()["artifact_index"]["entries"]}
    expected = {"WMBR", "AIS", "LEB", "ORP", "SQP", "EWP", "OEC", "OES", "DIB", "DTX"}
    assert expected <= families


def test_sle_rc_consolidation_disabled_capabilities():
    disabled = _consolidation()["disabled_capabilities"]
    assert disabled["pdf_ingestion_enabled"] is False
    assert disabled["ocr_ingestion_enabled"] is False
    assert disabled["automatic_belief_promotion"] is False


def test_sle_rc_consolidation_no_deployment_claim():
    summary = _consolidation()["chain_summary"]
    assert summary["system_may_not_deploy_itself"] is True
    assert summary["system_may_not_claim_truth"] is True


def test_sle_rc_consolidation_phase_links_present():
    for phase in _consolidation()["phase_index"]:
        assert phase["test"]
        assert phase["gate"]
        assert phase["report"]
