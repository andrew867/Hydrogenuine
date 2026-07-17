"""OEC-0 schema and policy tests."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.fixtures import build_oec0_fixture_records
from hg_runtime.operator_evidence_corpus.gate import validate_oec0_gate
from hg_runtime.operator_evidence_corpus.redaction import secret_scan
from hg_runtime.operator_evidence_corpus.schemas import (
    CLAIM_FAMILY_IDS,
    EXPECTED_OUTCOME_TYPES,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RECORD_TYPES,
)


def _records():
    return build_oec0_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_OEC_0_SCHEMA_POLICY",
        "ewp_consolidation_green": True,
        "schemas_declared": True,
        "corpus_written": True,
        "manifest_written": True,
        "source_written": True,
        "claim_written": True,
        "packet_written": True,
        "outcome_written": True,
        "policy_written": True,
        "corpus_not_truth": True,
        "source_not_authority": True,
        "fixture_not_world": True,
        "outcome_not_truth": True,
        "policy_no_arbitrary_ingestion": True,
        "no_pdf_ocr": True,
        "no_belief_promotion": True,
        "no_authority": True,
        "no_tools": True,
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


def test_oec0_declares_required_record_types():
    expected = {
        "operator_evidence_corpus_v1",
        "corpus_manifest_v1",
        "corpus_source_v1",
        "corpus_claim_v1",
        "corpus_claim_packet_v1",
        "corpus_expected_outcome_v1",
        "corpus_boundary_policy_v1",
        "corpus_gate_result_v1",
    }
    assert expected <= RECORD_TYPES


def test_oec0_builds_all_schema_records():
    records = _records()
    assert records["operator_evidence_corpus"]
    assert records["corpus_manifest"]
    assert records["corpus_sources"]
    assert records["corpus_claims"]
    assert records["corpus_expected_outcomes"]
    assert records["corpus_claim_packets"]
    assert records["corpus_boundary_policy"]


def test_oec0_claim_families_declared():
    assert len(CLAIM_FAMILY_IDS) == 10
    assert len(EXPECTED_OUTCOME_TYPES) == 10


def test_oec0_corpus_is_not_truth():
    assert _records()["operator_evidence_corpus"]["corpus_treated_as_truth"] is False


def test_oec0_source_is_not_authority():
    assert all(not row["corpus_source_treated_as_authority"] for row in _records()["corpus_sources"])


def test_oec0_fixture_is_not_world():
    assert _records()["corpus_manifest"]["fixture_corpus_treated_as_world"] is False


def test_oec0_outcome_is_not_truth():
    assert all(not row["expected_outcome_treated_as_truth"] for row in _records()["corpus_expected_outcomes"])


def test_oec0_policy_blocks_arbitrary_ingestion():
    policy = _records()["corpus_boundary_policy"]
    assert policy["arbitrary_file_ingestion_enabled"] is False
    assert policy["directory_crawling_enabled"] is False
    assert policy["pdf_ingestion_enabled"] is False


def test_oec0_no_belief_promotion_or_tools():
    rows = [item for value in _records().values() for item in (value if isinstance(value, list) else [value]) if isinstance(item, dict)]
    assert all(not row["belief_promotion_automatic"] for row in rows)
    assert all(not row["tools_authorized"] for row in rows)


def test_oec0_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_oec0_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_oec0_gate_passes():
    assert validate_oec0_gate(_summary())["ok"] is True


def test_oec0_gate_refuses_corpus_as_truth():
    assert validate_oec0_gate(_summary(corpus_treated_as_truth=True))["ok"] is False
