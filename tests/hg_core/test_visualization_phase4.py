"""
Tests for Visualization Phase 4: explorable explainers (decision explainer, compare, proof-path).
"""
from pathlib import Path

import pytest

from hg_core.viz import (
    get_viz_decision_explainer,
    get_viz_compare_decisions,
    get_viz_proof_path,
    adapt_decision_explainer,
    adapt_compare_decisions,
    adapt_proof_path,
)


def test_get_viz_decision_explainer_shape(tmp_path: Path) -> None:
    """Decision explainer returns dict with decision_id, based_on_claim_ids, value_weights, etc."""
    out = get_viz_decision_explainer(tmp_path, "no-such-decision")
    assert isinstance(out, dict)
    assert "decision_id" in out
    assert "based_on_claim_ids" in out
    assert "value_weights" in out
    assert "context_ref" in out
    assert "produced_artifact_ids" in out
    assert "title" in out
    assert "event_id" in out


def test_get_viz_decision_explainer_missing_decision(tmp_path: Path) -> None:
    """Missing decision returns empty/None fields."""
    out = get_viz_decision_explainer(tmp_path, "missing-id")
    assert out["decision_id"] == "missing-id"
    assert out["based_on_claim_ids"] == []
    assert out["event_id"] is None or isinstance(out["event_id"], str)


def test_get_viz_compare_decisions_shape(tmp_path: Path) -> None:
    """Compare decisions returns decision_id_a, decision_id_b, overlapping_claim_ids, value_weight_diffs."""
    out = get_viz_compare_decisions(tmp_path, "a", "b")
    assert isinstance(out, dict)
    assert out["decision_id_a"] == "a"
    assert out["decision_id_b"] == "b"
    assert "overlapping_claim_ids" in out
    assert "value_weight_diffs" in out
    assert "same_facts_different_action" in out
    assert isinstance(out["overlapping_claim_ids"], list)
    assert isinstance(out["value_weight_diffs"], list)


def test_get_viz_proof_path_shape(tmp_path: Path) -> None:
    """Proof path returns decision_id, decision, predictions, evaluations, self_assessments."""
    out = get_viz_proof_path(tmp_path, "no-such-decision")
    assert isinstance(out, dict)
    assert out["decision_id"] == "no-such-decision"
    assert "decision" in out
    assert "predictions" in out
    assert "evaluations" in out
    assert "self_assessments" in out
    assert isinstance(out["decision"], dict)
    assert isinstance(out["predictions"], list)
    assert isinstance(out["evaluations"], list)
    assert isinstance(out["self_assessments"], list)


def test_adapt_decision_explainer(tmp_path: Path) -> None:
    """Adapter decision explainer returns same shape as API."""
    out = adapt_decision_explainer(tmp_path, "x")
    assert "decision_id" in out
    assert out["decision_id"] == "x"


def test_adapt_compare_decisions(tmp_path: Path) -> None:
    """Adapter compare decisions returns required keys."""
    out = adapt_compare_decisions(tmp_path, "id1", "id2")
    assert out["decision_id_a"] == "id1"
    assert out["decision_id_b"] == "id2"
    assert "same_facts_different_action" in out


def test_adapt_proof_path(tmp_path: Path) -> None:
    """Adapter proof path returns decision, predictions, evaluations, self_assessments."""
    out = adapt_proof_path(tmp_path, "d1")
    assert out["decision_id"] == "d1"
    assert "decision" in out
    assert "predictions" in out
    assert "evaluations" in out
    assert "self_assessments" in out
