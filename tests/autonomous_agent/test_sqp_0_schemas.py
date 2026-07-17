"""SQP-0 schema foundation tests."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.fixtures import build_sqp0_fixture_records
from hg_runtime.source_quality_provenance.gate import validate_sqp0_gate
from hg_runtime.source_quality_provenance.redaction import secret_scan
from hg_runtime.source_quality_provenance.schemas import PHASE19_VERDICT, PHASE24_STATUS, RECORD_TYPES


def _records():
    return build_sqp0_fixture_records()


def _summary(**overrides):
    data = {
        "verdict": "GREEN_SQP_0_SCHEMA_FOUNDATION",
        "reviewed_beta_green": True,
        "schemas_declared": True,
        "source_identity_written": True,
        "source_fingerprint_written": True,
        "duplicate_record_written": True,
        "quality_score_written": True,
        "provenance_records_written": True,
        "staleness_record_written": True,
        "conflict_record_written": True,
        "redaction_status_written": True,
        "quarantine_history_written": True,
        "review_hint_written": True,
        "source_quality_not_truth": True,
        "provenance_not_authority": True,
        "duplicate_not_corroboration": True,
        "many_copies_not_many_sources": True,
        "stale_not_false": True,
        "low_quality_not_deletion": True,
        "review_hint_not_approval": True,
        "no_belief_promotion": True,
        "no_authority": True,
        "no_tools": True,
        "no_live_effects": True,
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


def test_sqp0_declares_required_record_types():
    expected = {
        "source_identity_v1",
        "source_fingerprint_v1",
        "duplicate_source_record_v1",
        "source_quality_score_v1",
        "provenance_node_v1",
        "provenance_edge_v1",
        "provenance_graph_v1",
        "source_staleness_record_v1",
        "source_conflict_record_v1",
        "source_redaction_status_v1",
        "source_quarantine_history_v1",
        "source_review_policy_hint_v1",
        "sqp_gate_result_v1",
    }
    assert expected <= RECORD_TYPES


def test_sqp0_builds_all_schema_records():
    records = _records()
    assert records["source_identities"]
    assert records["source_fingerprints"]
    assert records["duplicate_source_records"]
    assert records["source_quality_scores"]
    assert records["provenance_nodes"]
    assert records["provenance_edges"]
    assert records["provenance_graph"]
    assert records["source_staleness_records"]
    assert records["source_conflict_records"]
    assert records["source_redaction_status"]
    assert records["source_quarantine_history"]
    assert records["source_review_policy_hints"]


def test_sqp0_source_quality_is_not_truth():
    assert all(not row["source_quality_treated_as_truth"] for row in _records()["source_quality_scores"])


def test_sqp0_provenance_is_not_authority():
    records = _records()
    assert records["provenance_graph"]["provenance_treated_as_authority"] is False
    assert all(not row["provenance_treated_as_authority"] for row in records["provenance_nodes"])


def test_sqp0_duplicate_is_not_corroboration():
    duplicate = _records()["duplicate_source_records"][0]
    assert duplicate["duplicate_treated_as_corroboration"] is False
    assert duplicate["independent_corroboration_count"] == 1


def test_sqp0_many_copies_are_not_many_sources():
    graph = _records()["provenance_graph"]
    assert graph["distinct_source_count"] == 2


def test_sqp0_stale_source_is_not_false():
    assert all(not row["stale_source_treated_as_false"] for row in _records()["source_staleness_records"])


def test_sqp0_low_quality_is_not_deletion_permission():
    assert all(not row["low_quality_deletion_permission"] for row in _records()["source_quality_scores"])


def test_sqp0_review_hint_is_not_operator_approval():
    assert all(not row["review_hint_treated_as_operator_approval"] for row in _records()["source_review_policy_hints"])


def test_sqp0_no_belief_promotion_authority_tools_live_effects():
    rows = [item for value in _records().values() for item in (value if isinstance(value, list) else [value])]
    assert all(not row["belief_promotion_automatic"] for row in rows)
    assert all(not row["authority_granted"] for row in rows)
    assert all(not row["tools_authorized"] for row in rows)
    assert all(not row["live_external_side_effects_created"] for row in rows)


def test_sqp0_no_web_or_provider():
    rows = [item for value in _records().values() for item in (value if isinstance(value, list) else [value])]
    assert all(not row["web_browse_performed"] for row in rows)
    assert all(not row["external_provider_calls_made"] for row in rows)


def test_sqp0_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_sqp0_secret_scan_passes():
    assert secret_scan(_records()) is True


def test_sqp0_gate_passes_full_summary():
    assert validate_sqp0_gate(_summary())["ok"] is True


def test_sqp0_gate_refuses_quality_as_truth():
    assert validate_sqp0_gate(_summary(source_quality_treated_as_truth=True))["ok"] is False


def test_sqp0_gate_refuses_provenance_authority():
    assert validate_sqp0_gate(_summary(provenance_treated_as_authority=True))["ok"] is False


def test_sqp0_gate_refuses_duplicate_corroboration():
    assert validate_sqp0_gate(_summary(duplicate_treated_as_corroboration=True))["ok"] is False


def test_sqp0_gate_refuses_belief_promotion():
    assert validate_sqp0_gate(_summary(belief_promotion_automatic=True))["ok"] is False


def test_sqp0_gate_refuses_authority_or_tools():
    assert validate_sqp0_gate(_summary(authority_granted=True))["ok"] is False
    assert validate_sqp0_gate(_summary(tools_authorized=True))["ok"] is False


def test_sqp0_gate_refuses_without_reviewed_beta():
    assert validate_sqp0_gate(_summary(reviewed_beta_green=False))["ok"] is False
