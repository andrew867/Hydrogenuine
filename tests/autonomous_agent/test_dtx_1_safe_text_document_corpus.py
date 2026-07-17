"""DTX-1 safe text document corpus tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.document_text_exchange.fixtures import build_dtx1_corpus_layer
from hg_runtime.document_text_exchange.gate import validate_dtx1_gate
from hg_runtime.document_text_exchange.schemas import DOCUMENT_FIXTURE_FAMILIES

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return build_dtx1_corpus_layer(root=ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_DTX_1_SAFE_TEXT_DOCUMENT_CORPUS",
        "dib_consolidation_green": True,
        "dtx0_green": True,
        "all_families_present": True,
        "manifest_written": True,
        "fixtures_written": True,
        "outcomes_written": True,
        "validation_passed": True,
        "corpus_not_truth": True,
        "outcome_not_proof": True,
        "duplicate_not_corroboration": True,
        "stale_not_false": True,
        "no_pdf_ocr_html_binary": True,
        "no_arbitrary_ingestion": True,
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


def test_dtx1_all_families_present():
    families = {row["family_id"] for row in _layer()["dtx_expected_outcomes"]}
    assert families == DOCUMENT_FIXTURE_FAMILIES


def test_dtx1_validation_passes():
    assert _layer()["validation"]["ok"] is True


def test_dtx1_corpus_not_world():
    assert _layer()["dtx_manifest"]["document_corpus_treated_as_world"] is False


def test_dtx1_replay_preserves_manifest_hash():
    layer = _layer()
    assert layer["replay"]["manifest_hash"] == layer["dtx_manifest"]["manifest_hash"]


def test_dtx1_gate_passes():
    assert validate_dtx1_gate(_summary())["ok"] is True
