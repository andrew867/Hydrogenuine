"""OEC-2 corpus-to-LEB harness tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_corpus.corpus_ingestion_harness import ingest_curated_corpus
from hg_runtime.operator_evidence_corpus.gate import validate_oec2_gate
from hg_runtime.operator_evidence_corpus.redaction import secret_scan

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return ingest_curated_corpus(ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_OEC_2_CORPUS_TO_LEB_HARNESS",
        "ewp_consolidation_green": True,
        "oec1_green": True,
        "explicit_manifest_only": True,
        "no_directory_crawling": True,
        "no_path_traversal": True,
        "no_symlink_escape": True,
        "no_pdf_ocr_binary": True,
        "receipts_written": True,
        "excerpts_written": True,
        "receipt_not_truth": True,
        "no_belief_promotion": True,
        "no_tool_authorization": True,
        "no_web_or_provider": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_receipt_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_oec2_ingests_explicit_manifest_only():
    layer = _layer()
    assert layer["corpus_leb_ingestion_manifest"]["only_explicit_paths"] is True
    assert len(layer["corpus_evidence_receipts"]) == len(layer["corpus_leb_ingestion_manifest"]["explicit_source_paths"])


def test_oec2_receipt_is_not_truth():
    assert all(not row["evidence_receipt_is_truth"] for row in _layer()["corpus_evidence_receipts"])


def test_oec2_redaction_family_present():
    redacted = [row for row in _layer()["corpus_evidence_receipts"] if row["secret_like_content_redacted"]]
    assert redacted


def test_oec2_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_oec2_gate_passes():
    assert validate_oec2_gate(_summary())["ok"] is True
