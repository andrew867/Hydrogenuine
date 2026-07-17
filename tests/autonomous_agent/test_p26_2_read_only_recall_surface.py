"""P26-2 read-only recall surface tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.experience_ledger.gate import validate_p26_2_gate
from hg_runtime.experience_ledger.recall_index import build_recall_index
from hg_runtime.experience_ledger.recall_query import make_query
from hg_runtime.experience_ledger.recall_replay import replay_recall
from hg_runtime.experience_ledger.recall_surface import run_recall_query
from hg_runtime.experience_ledger.schemas import ExperienceLedgerBoundaryError, RECALL_QUERY_TYPES, assert_neutral


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P26_2_READ_ONLY_RECALL_SURFACE",
        "recall_query_types_declared": True,
        "recall_index_written": True,
        "recall_queries_written": True,
        "recall_results_written": True,
        "recall_manifest_written": True,
        "recall_returns_provenance_pointers": True,
        "recall_read_only": True,
        "memory_is_not_truth": True,
        "recall_is_not_authority": True,
        "recall_cannot_authorize_tools": True,
        "recall_cannot_promote_beliefs": True,
        "recall_cannot_delete": True,
        "retracted_memory_handled": True,
        "quarantined_memory_handled": True,
        "replay_stable": True,
        "fake_truth_authority_rejected": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p26_2_recall_query_types_declared():
    assert {
        "by_family",
        "by_verdict",
        "by_boundary_tag",
        "by_artifact_id",
        "by_time_window",
        "by_risk_tag",
        "by_retraction_status",
        "by_quarantine_status",
    } == RECALL_QUERY_TYPES


def test_p26_2_builds_recall_index():
    index = build_recall_index(Path.cwd())
    assert index["index"]["entry_count"] == 3


def test_p26_2_recall_by_family_returns_provenance():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_family", "SLE-RC"), index)
    assert result["result_count"] == 1
    assert result["provenance_refs"]


def test_p26_2_recall_by_verdict():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_verdict", "GREEN_PHASE25_ADVISORY_SELF_IMPROVEMENT"), index)
    assert result["memory_refs"] == ["mem-artifact-phase25"]


def test_p26_2_recall_by_boundary_tag():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_boundary_tag", "p26_not_complete"), index)
    assert result["memory_refs"] == ["mem-artifact-p26-gap"]


def test_p26_2_recall_by_artifact_id():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_artifact_id", "artifact-sle-rc"), index)
    assert result["memory_refs"] == ["mem-artifact-sle-rc"]


def test_p26_2_recall_by_time_window():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_time_window", "ALL_FIXTURE_TIME"), index)
    assert result["result_count"] == 3


def test_p26_2_recall_by_risk_tag():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_risk_tag", "gap_analysis_not_completion"), index)
    assert result["memory_refs"] == ["mem-artifact-p26-gap"]


def test_p26_2_recall_handles_retracted_memory():
    index = build_recall_index(Path.cwd())["index"]
    index["entries"][0]["retraction_status"] = "RETRACTED"
    result = run_recall_query(make_query("by_retraction_status", "RETRACTED"), index)
    assert result["memory_refs"] == ["mem-artifact-sle-rc"]


def test_p26_2_recall_handles_quarantined_memory():
    index = build_recall_index(Path.cwd())["index"]
    index["entries"][0]["quarantine_status"] = "QUARANTINED"
    result = run_recall_query(make_query("by_quarantine_status", "QUARANTINED"), index)
    assert result["memory_refs"] == ["mem-artifact-sle-rc"]


def test_p26_2_recall_is_read_only_not_truth_or_authority():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_family", "SLE-RC"), index)
    assert result["read_only"] is True
    assert result["memory_treated_as_truth"] is False
    assert result["recall_treated_as_authority"] is False


def test_p26_2_recall_cannot_authorize_tools_promote_or_delete():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_family", "SLE-RC"), index)
    assert result["tools_authorized"] is False
    assert result["belief_promoted"] is False
    assert result["deletion_performed"] is False


def test_p26_2_recall_replay_stable():
    index = build_recall_index(Path.cwd())
    queries = [make_query("by_family", "SLE-RC")]
    replay = replay_recall(queries, index["index"])
    assert replay["replay_preserves_recall_hashes"] is True


def test_p26_2_recall_replay_detects_mutated_index():
    index = build_recall_index(Path.cwd())
    queries = [make_query("by_family", "SLE-RC")]
    baseline = replay_recall(queries, index["index"])["recall_replay_root"]
    index["index"]["entries"][0]["family"] = "MUTATED"
    replay = replay_recall(queries, index["index"], expected_root=baseline)
    assert replay["replay_preserves_recall_hashes"] is False


def test_p26_2_rejects_invalid_query_type():
    with pytest.raises(ExperienceLedgerBoundaryError):
        make_query("by_truth", "yes")


def test_p26_2_rejects_fake_truth_authority_result():
    index = build_recall_index(Path.cwd())["index"]
    result = run_recall_query(make_query("by_family", "SLE-RC"), index)
    result["recall_treated_as_authority"] = True
    with pytest.raises(ExperienceLedgerBoundaryError):
        assert_neutral(result)


def test_p26_2_gate_passes_full_summary():
    assert validate_p26_2_gate(_summary())["ok"] is True


def test_p26_2_gate_refuses_memory_truth():
    assert validate_p26_2_gate(_summary(memory_treated_as_truth=True))["ok"] is False


def test_p26_2_gate_refuses_recall_authority():
    assert validate_p26_2_gate(_summary(recall_treated_as_authority=True))["ok"] is False


def test_p26_2_gate_refuses_tool_authorization():
    assert validate_p26_2_gate(_summary(tools_authorized=True))["ok"] is False


def test_p26_2_gate_refuses_belief_promotion():
    assert validate_p26_2_gate(_summary(belief_promoted=True))["ok"] is False


def test_p26_2_gate_refuses_deletion():
    assert validate_p26_2_gate(_summary(deletion_performed=True))["ok"] is False


def test_p26_2_gate_refuses_without_proof_bundle():
    assert validate_p26_2_gate(_summary(proof_bundle_valid=False))["ok"] is False

