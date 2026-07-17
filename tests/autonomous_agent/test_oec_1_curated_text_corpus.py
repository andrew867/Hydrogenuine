"""OEC-1 curated text corpus tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_corpus.corpus_validator import validate_curated_corpus
from hg_runtime.operator_evidence_corpus.curated_corpus_builder import build_curated_corpus
from hg_runtime.operator_evidence_corpus.gate import validate_oec1_gate
from hg_runtime.operator_evidence_corpus.redaction import secret_scan
from hg_runtime.operator_evidence_corpus.schemas import CLAIM_FAMILY_IDS, PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _records():
    return build_curated_corpus()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_OEC_1_CURATED_TEXT_CORPUS",
        "ewp_consolidation_green": True,
        "oec0_green": True,
        "all_families_present": True,
        "manifest_written": True,
        "sources_written": True,
        "claims_written": True,
        "outcomes_written": True,
        "validation_passed": True,
        "corpus_not_truth": True,
        "outcome_not_proof": True,
        "duplicate_not_corroboration": True,
        "stale_not_false": True,
        "contradiction_not_resolved": True,
        "low_quality_not_deletion": True,
        "high_quality_not_certainty": True,
        "no_arbitrary_ingestion": True,
        "no_pdf_ocr": True,
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


def test_oec1_covers_all_families():
    families = {row["family_id"] for row in _records()["corpus_claims"]}
    assert families == CLAIM_FAMILY_IDS


def test_oec1_validates_fixture_paths():
    assert validate_curated_corpus(ROOT, _records())["ok"] is True


def test_oec1_corpus_is_not_truth():
    assert not _records()["operator_evidence_corpus"]["corpus_treated_as_truth"]


def test_oec1_outcome_is_not_proof():
    assert all(not row["expected_outcome_treated_as_proof"] for row in _records()["corpus_expected_outcomes"])


def test_oec1_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_oec1_gate_passes():
    assert validate_oec1_gate(_summary())["ok"] is True
