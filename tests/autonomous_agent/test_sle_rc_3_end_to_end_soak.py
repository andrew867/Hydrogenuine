"""SLE-RC-3 end-to-end soak tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.gate import validate_sle_rc3_gate
from hg_runtime.safe_local_evidence_rc.rc_soak_runner import run_rc_soak
from hg_runtime.safe_local_evidence_rc.schemas import RC_SOAK_ITERATION_COUNT

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return run_rc_soak(ROOT, iteration_count=RC_SOAK_ITERATION_COUNT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SLE_RC_3_END_TO_END_SOAK",
        "sle_rc2_green": True,
        "soak_iterations_written": True,
        "minimum_iterations_met": True,
        "stable_hashes_written": True,
        "replay_result_written": True,
        "mutation_summary_written": True,
        "soak_not_truth": True,
        "replay_not_truth": True,
        "mutation_not_repair": True,
        "no_pdf_ocr": True,
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


def test_sle_rc3_runs_minimum_iterations():
    assert len(_layer()["rc_soak_iterations"]) >= RC_SOAK_ITERATION_COUNT


def test_sle_rc3_all_iterations_match():
    layer = _layer()
    assert all(row["replay_match"] for row in layer["rc_soak_iterations"])


def test_sle_rc3_consumes_explicit_manifests_only():
    layer = _layer()
    assert layer["manifest_refs"]["explicit_manifest_only"] is True
    assert layer["rc_soak_manifest"]["explicit_manifest_only"] is True


def test_sle_rc3_mutation_not_repair():
    layer = _layer()
    assert layer["rc_mutation_summary"]["mutation_auto_repaired"] is False
    assert layer["rc_mutation_summary"]["mutation_detection_is_repair"] is False


def test_sle_rc3_records_component_replay_status():
    layer = _layer()
    replay = layer["rc_replay_result"]["component_replay_status"]
    assert "dib_replay_status" in replay
    assert "oes_replay_status" in replay
    assert "dtx_replay_status" in replay


def test_sle_rc3_gate_passes():
    assert validate_sle_rc3_gate(_summary())["ok"] is True
