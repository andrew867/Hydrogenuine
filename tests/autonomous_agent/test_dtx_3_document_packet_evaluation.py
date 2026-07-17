"""DTX-3 document packet evaluation tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.document_text_exchange.dtx_dib_runner import run_dtx_dib_extraction
from hg_runtime.document_text_exchange.dtx_packet_evaluation import evaluate_document_packets
from hg_runtime.document_text_exchange.gate import validate_dtx3_gate

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    bridge = run_dtx_dib_extraction(ROOT)
    return evaluate_document_packets(bridge)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DTX_3_DOCUMENT_PACKET_EVALUATION",
        "dib_consolidation_green": True,
        "dtx2_green": True,
        "packets_written": True,
        "second_source_written": True,
        "contradiction_written": True,
        "dashboard_written": True,
        "packet_not_truth": True,
        "second_source_not_truth": True,
        "contradiction_not_resolution": True,
        "dashboard_not_approval": True,
        "no_belief_promotion": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_dtx3_builds_ten_packets():
    assert len(_layer()["dtx_claim_packets"]) == 10


def test_dtx3_packet_not_truth():
    layer = _layer()
    assert all(not row.get("packet_treated_as_truth", False) for row in layer["dtx_claim_packets"])


def test_dtx3_dashboard_not_approval():
    assert _layer()["dtx_operator_dashboard"]["dashboard_treated_as_operator_approval"] is False


def test_dtx3_gate_passes():
    assert validate_dtx3_gate(_summary())["ok"] is True
