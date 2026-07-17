"""SLE-RC-X extended regression soak tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.gate import validate_sle_rc_extended_gate
from hg_runtime.safe_local_evidence_rc.rc_churn_analyzer import analyze_churn
from hg_runtime.safe_local_evidence_rc.rc_extended_soak import (
    EXTENDED_SOAK_ITERATION_COUNT,
    run_extended_soak,
)
from hg_runtime.safe_local_evidence_rc.rc_regression_matrix import build_regression_matrix

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return run_extended_soak(ROOT, iteration_count=EXTENDED_SOAK_ITERATION_COUNT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SLE_RC_EXTENDED_REGRESSION_SOAK",
        "sle_rc_consolidation_green": True,
        "minimum_iterations_met": True,
        "extended_iterations_written": True,
        "stable_hashes_written": True,
        "churn_analysis_written": True,
        "boundary_matrix_replays_written": True,
        "extended_replay_result_written": True,
        "regression_matrix_written": True,
        "all_iterations_match": True,
        "iterations_stable": True,
        "boundary_matrix_stable": True,
        "regression_all_paths_green": True,
        "oec_corpus_path_included": True,
        "dtx_safe_text_path_included": True,
        "oes_mutation_summary_path_included": True,
        "no_unexpected_churn": True,
        "soak_not_truth": True,
        "replay_not_truth": True,
        "mutation_not_repair": True,
        "no_new_ingestion_capability": True,
        "no_pdf_ocr": True,
        "no_html": True,
        "no_arbitrary_ingestion": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Soak behavior ---------------------------------------------------------

def test_extended_soak_runs_at_least_10_iterations():
    layer = _layer()
    assert len(layer["rc_extended_soak_iterations"]) >= 10
    assert layer["rc_extended_soak_manifest"]["iteration_count"] >= EXTENDED_SOAK_ITERATION_COUNT


def test_extended_soak_all_iterations_match_and_stable():
    layer = _layer()
    assert all(row["replay_match"] for row in layer["rc_extended_soak_iterations"])
    assert layer["rc_extended_replay_result"]["iterations_stable"] is True
    assert layer["rc_extended_stable_hashes"]["all_iteration_hashes_equal"] is True


def test_extended_soak_includes_oec_dtx_oes_paths():
    m = _layer()["rc_extended_soak_manifest"]
    assert m["oec_corpus_path_included"] is True
    assert m["dtx_safe_text_path_included"] is True
    assert m["oes_mutation_summary_path_included"] is True


def test_extended_soak_boundary_matrix_replayed_per_iteration():
    layer = _layer()
    replays = layer["rc_boundary_matrix_replays"]
    assert len(replays) >= 10
    assert layer["rc_extended_replay_result"]["boundary_matrix_stable"] is True
    assert all(r["phase19_yellow_preserved"] for r in replays)
    assert all(r["phase24_infrastructure_only_preserved"] for r in replays)


def test_extended_soak_no_unexpected_churn():
    churn = _layer()["rc_churn_analysis"]
    assert churn["unexpected_churn_detected"] is False
    assert churn["iteration_hash_drift_detected"] is False
    assert churn["boundary_matrix_drift_detected"] is False


def test_extended_soak_mutation_not_repair():
    layer = _layer()
    assert layer["rc_mutation_summary"]["mutation_auto_repaired"] is False
    assert layer["rc_extended_replay_result"]["mutation_auto_repaired"] is False


def test_extended_soak_no_new_ingestion_surface():
    m = _layer()["rc_extended_soak_manifest"]
    assert m["no_new_ingestion_capability"] is True
    assert m["pdf_ingestion_enabled"] is False
    assert m["ocr_ingestion_enabled"] is False
    assert m["html_parsing_enabled"] is False
    assert m["arbitrary_file_ingestion_enabled"] is False


# --- Regression matrix -----------------------------------------------------

def test_regression_matrix_all_paths_green():
    matrix = build_regression_matrix(ROOT)
    assert matrix["all_paths_green"] is True
    assert matrix["path_count"] == 3


# --- Churn analyzer --------------------------------------------------------

def test_churn_analyzer_flags_drift():
    drift = analyze_churn(
        iteration_hashes=["a", "a", "b"],
        boundary_matrix_hashes=["m", "m"],
        regression_matrix_hash="r",
    )
    assert drift["iteration_hash_drift_detected"] is True
    assert drift["unexpected_churn_detected"] is True


def test_churn_analyzer_clean_when_stable():
    clean = analyze_churn(
        iteration_hashes=["a", "a", "a"],
        boundary_matrix_hashes=["m", "m"],
        regression_matrix_hash="r",
    )
    assert clean["unexpected_churn_detected"] is False


# --- Gate ------------------------------------------------------------------

def test_extended_gate_passes_full_summary():
    assert validate_sle_rc_extended_gate(_summary())["ok"] is True


def test_extended_gate_refuses_unexpected_churn():
    assert validate_sle_rc_extended_gate(_summary(no_unexpected_churn=False, unexpected_churn_detected=True))["ok"] is False


def test_extended_gate_refuses_soak_as_truth():
    assert validate_sle_rc_extended_gate(_summary(soak_treated_as_truth=True))["ok"] is False


def test_extended_gate_refuses_mutation_auto_repair():
    assert validate_sle_rc_extended_gate(_summary(mutation_auto_repaired=True))["ok"] is False


def test_extended_gate_refuses_new_ingestion():
    assert validate_sle_rc_extended_gate(_summary(pdf_ingestion_enabled=True))["ok"] is False
    assert validate_sle_rc_extended_gate(_summary(html_parsing_enabled=True))["ok"] is False


def test_extended_gate_refuses_missing_paths():
    assert validate_sle_rc_extended_gate(_summary(oec_corpus_path_included=False))["ok"] is False
    assert validate_sle_rc_extended_gate(_summary(oes_mutation_summary_path_included=False))["ok"] is False
