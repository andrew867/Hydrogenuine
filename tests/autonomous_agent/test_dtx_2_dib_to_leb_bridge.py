"""DTX-2 DIB to LEB bridge tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.document_text_exchange.dtx_bridge_replay import replay_bridge_layer
from hg_runtime.document_text_exchange.dtx_dib_runner import run_dtx_dib_extraction
from hg_runtime.document_text_exchange.gate import validate_dtx2_gate

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    layer = run_dtx_dib_extraction(ROOT)
    layer["replay"] = replay_bridge_layer(layer)
    return layer


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DTX_2_DIB_TO_LEB_BRIDGE",
        "dib_consolidation_green": True,
        "dtx1_green": True,
        "explicit_manifest_only": True,
        "receipts_written": True,
        "failures_written": True,
        "bridge_written": True,
        "receipt_not_truth": True,
        "bridge_not_promotion": True,
        "identity_not_filename": True,
        "metadata_not_provenance": True,
        "hash_not_truth": True,
        "no_pdf_ocr": True,
        "no_web_or_provider": True,
        "no_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_dtx2_extracts_safe_text_receipts():
    layer = _layer()
    assert len(layer["dtx_extraction_receipts"]) >= 10


def test_dtx2_records_json_extraction_failure():
    layer = _layer()
    assert len(layer["dtx_extraction_failures"]) >= 1


def test_dtx2_bridge_not_belief_promotion():
    layer = _layer()
    assert all(not row["dib_adapter_treated_as_belief_promotion"] for row in layer["dtx_leb_bridge_records"])


def test_dtx2_replay_deterministic():
    assert _layer()["replay"]["replay_deterministic"] is True


def test_dtx2_gate_passes():
    assert validate_dtx2_gate(_summary())["ok"] is True
