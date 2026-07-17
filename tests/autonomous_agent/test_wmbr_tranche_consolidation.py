"""WMBR tranche consolidation handoff tests (docs/report only)."""

from __future__ import annotations

from pathlib import Path

from scripts.evals.autonomous_agent_wmbr_tranche_consolidation_gate import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PHASES,
    VERDICT_GREEN,
    collect_phase_entries,
    validate_consolidation,
)

ROOT = Path(__file__).resolve().parents[2]


def test_wmbr_tranche_has_six_phases():
    assert len(PHASES) == 6


def test_wmbr_tranche_collects_all_phase_entries():
    entries = collect_phase_entries()
    assert len(entries) == 6
    assert all(e["proof_bundle_exists"] for e in entries)
    assert all(e["gate_green"] for e in entries)
    assert all(e["report_exists"] for e in entries)


def test_wmbr_tranche_consolidation_validates_green():
    entries = collect_phase_entries()
    result = validate_consolidation(entries)
    assert result["ok"] is True
    assert result["failures"] == []


def test_wmbr_tranche_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_wmbr_tranche_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_wmbr_tranche_expected_verdict_string():
    assert VERDICT_GREEN == "GREEN_WMBR_TRANCHE_CONSOLIDATION_HANDOFF"


def test_wmbr_tranche_wmbr01_not_completed_in_entries():
    entries = collect_phase_entries()
    for e in entries:
        assert e["gate_verdict"].startswith("GREEN_WMBR")
