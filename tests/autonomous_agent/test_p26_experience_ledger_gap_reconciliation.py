"""P26 persistent memory / experience ledger gap reconciliation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.generalist_gap_reconciliation.gate import validate_p26_gap_gate
from hg_runtime.generalist_gap_reconciliation.p26_gap_mapper import (
    build_gap_record,
    build_p26_layer,
    replay_p26,
)
from hg_runtime.generalist_gap_reconciliation.schemas import (
    GAP_STATUSES,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    P26GapBoundaryError,
)
from hg_runtime.safe_local_evidence_rc.redaction import secret_scan

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return build_p26_layer(ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P26_EXPERIENCE_LEDGER_GAP_RECONCILIATION",
        "acceptance_criteria_written": True,
        "existing_artifact_map_written": True,
        "gap_records_written": True,
        "recommendation_records_written": True,
        "all_gap_statuses_exercised": True,
        "requires_exact_p26_present": True,
        "gap_analysis_not_completion": True,
        "partial_not_green": True,
        "existing_artifacts_do_not_auto_complete": True,
        "p26_not_marked_complete": True,
        "no_authority_change": True,
        "no_new_ingestion": True,
        "no_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_manifest_hash": True,
        "replay_preserves_gap_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Mapping ---------------------------------------------------------------

def test_p26_maps_all_criteria():
    layer = _layer()
    assert layer["acceptance_criteria"]
    assert len(layer["gap_records"]) == len(layer["acceptance_criteria"])
    assert layer["existing_artifact_map"]


def test_p26_all_gap_statuses_exercised():
    statuses = {g["gap_status"] for g in _layer()["gap_records"]}
    assert GAP_STATUSES <= statuses


def test_p26_requires_exact_implementation_for_unified_gate():
    by_id = {g["criterion_id"]: g for g in _layer()["gap_records"]}
    assert by_id["P26-AC-8"]["gap_status"] == "REQUIRES_EXACT_P26_IMPLEMENTATION"


def test_p26_not_marked_complete():
    m = _layer()["manifest"]
    assert m["p26_complete"] is False
    assert m["p26_marked_complete"] is False
    assert m["exact_p26_gate_present"] is False
    assert m["non_completing_statuses_remain"] is True


def test_p26_satisfied_status_does_not_count_as_completion():
    for g in _layer()["gap_records"]:
        assert g["counts_as_p26_completion"] is False


def test_p26_existing_artifacts_present_for_satisfied():
    by_id = {g["criterion_id"]: g for g in _layer()["gap_records"]}
    # Replay determinism criterion is satisfied by an existing, present artifact.
    assert by_id["P26-AC-3"]["gap_status"] == "SATISFIED_BY_EXISTING_ARTIFACT"
    assert by_id["P26-AC-3"]["artifact_present"] is True


def test_p26_gap_record_rejects_unknown_status():
    with pytest.raises(P26GapBoundaryError):
        build_gap_record(criterion_id="x", title="t", status="NOPE", artifact_present=False, rationale="r")


def test_p26_conclusion_states_adapter_needed():
    assert "do not automatically" in _layer()["manifest"]["conclusion"]


# --- Replay ----------------------------------------------------------------

def test_p26_replay_preserves_hashes():
    layer = _layer()
    replay = replay_p26(
        ROOT,
        layer["manifest"]["manifest_hash"],
        [g["record_hash"] for g in layer["gap_records"]],
    )
    assert replay["replay_preserves_manifest_hash"] is True
    assert replay["replay_preserves_gap_hashes"] is True


def test_p26_replay_rejects_mutation():
    replay = replay_p26(ROOT, "mutated", ["mutated"])
    assert replay["replay_preserves_manifest_hash"] is False


def test_p26_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_p26_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_p26_gate_passes_full_summary():
    assert validate_p26_gap_gate(_summary())["ok"] is True


def test_p26_gate_refuses_p26_marked_complete():
    assert validate_p26_gap_gate(_summary(p26_not_marked_complete=False, p26_marked_complete=True))["ok"] is False


def test_p26_gate_refuses_gap_as_completion():
    assert validate_p26_gap_gate(_summary(gap_analysis_is_completion=True))["ok"] is False


def test_p26_gate_refuses_partial_as_green():
    assert validate_p26_gap_gate(_summary(partial_satisfaction_is_green=True))["ok"] is False


def test_p26_gate_refuses_auto_complete():
    assert validate_p26_gap_gate(_summary(existing_artifact_auto_completes_p26=True))["ok"] is False


def test_p26_gate_refuses_authority_or_ingestion():
    assert validate_p26_gap_gate(_summary(authority_changed=True))["ok"] is False
    assert validate_p26_gap_gate(_summary(new_ingestion_enabled=True))["ok"] is False


def test_p26_gate_refuses_missing_requires_exact():
    assert validate_p26_gap_gate(_summary(requires_exact_p26_present=False))["ok"] is False
