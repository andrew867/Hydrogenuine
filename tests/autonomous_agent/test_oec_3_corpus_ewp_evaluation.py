"""OEC-3 corpus EWP evaluation tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_corpus.corpus_ingestion_harness import ingest_curated_corpus
from hg_runtime.operator_evidence_corpus.corpus_packet_evaluation import evaluate_corpus_packets
from hg_runtime.operator_evidence_corpus.gate import validate_oec3_gate
from hg_runtime.operator_evidence_corpus.redaction import secret_scan

ROOT = Path(__file__).resolve().parents[2]


def _evaluation():
    return evaluate_corpus_packets(ingest_curated_corpus(ROOT))


def _summary(**overrides):
    data = {
        "verdict": "GREEN_OEC_3_CORPUS_EWP_EVALUATION",
        "ewp_consolidation_green": True,
        "oec2_green": True,
        "claim_packets_written": True,
        "second_source_results_written": True,
        "contradiction_packets_written": True,
        "dashboard_written": True,
        "packet_not_truth": True,
        "second_source_not_truth": True,
        "contradiction_not_resolution": True,
        "dashboard_not_approval": True,
        "expected_outcome_not_proof": True,
        "no_belief_promotion": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_manifest_hash": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_oec3_builds_claim_packets():
    evaluation = _evaluation()
    assert len(evaluation["corpus_claim_packets"]) == 10


def test_oec3_packet_is_not_truth():
    assert all(not row["packet_treated_as_truth"] for row in _evaluation()["corpus_claim_packets"])


def test_oec3_dashboard_is_not_approval():
    assert not _evaluation()["corpus_operator_dashboard"]["dashboard_treated_as_operator_approval"]


def test_oec3_secret_scan_passes():
    assert secret_scan(_evaluation()) is True


def test_oec3_gate_passes():
    assert validate_oec3_gate(_summary())["ok"] is True
