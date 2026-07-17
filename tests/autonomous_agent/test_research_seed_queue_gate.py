"""Tests for the research seed queue gate."""

from __future__ import annotations

import pytest

from hg_runtime.overnight_qa.research_seed_gate import run_gate


def test_gate_green_for_valid_seed_queue():
    result = run_gate()
    assert result["verdict"] == "GREEN_RESEARCH_SEED_QUEUE_EXPANDED", \
        [c for c in result["checks"] if not c["passed"]]


def test_gate_red_if_less_than_30_seeds(monkeypatch):
    import hg_runtime.overnight_qa.research_seed_gate as g
    monkeypatch.setattr(g, "build_research_seeds", lambda: [])
    result = g.run_gate()
    assert result["verdict"] != "GREEN_RESEARCH_SEED_QUEUE_EXPANDED"
    failed = [c["name"] for c in result["checks"] if not c["passed"]]
    assert "at_least_30_seeds" in failed


def test_gate_red_if_speculation_marked_fact():
    # The classifier flags speculation-as-fact; gate must require none.
    from hg_runtime.overnight_qa.research_seed_classifier import any_seed_marks_speculation_as_fact
    assert any_seed_marks_speculation_as_fact() is False


def test_gate_red_if_zero_selection_authorizes_task():
    from hg_runtime.overnight_qa.research_seed_queue import zero_rank_seeds
    r = zero_rank_seeds(["observer_state_frequency_hypothesis"])[0]
    # Zero ranking can never be self-approving.
    assert r.approved_by_runtime is False


def test_gate_red_if_browsing_allowed_without_source_policy():
    from hg_runtime.overnight_qa.research_seeds import build_research_seeds
    for s in build_research_seeds():
        if s.can_browse_later:
            assert s.source_policy_required is True


def test_gate_red_if_seed_promotes_without_knowledge_policy():
    from hg_runtime.overnight_qa.research_seeds import build_research_seeds
    for s in build_research_seeds():
        assert s.knowledge_policy_required is True
        assert s.can_promote_to_knowledge is False


def test_gate_preserves_phase19_yellow():
    result = run_gate()
    assert result["phase19_remains_yellow"] is True


def test_gate_preserves_phase24_infrastructure_only():
    result = run_gate()
    assert result["phase24_remains_infrastructure_only"] is True


def test_gate_zero_not_agi():
    result = run_gate()
    assert result["zero_is_not_agi"] is True
    assert result["zero_is_not_conscious"] is True
    assert result["zero_is_not_sovereign"] is True


def test_gate_seed_and_family_counts():
    result = run_gate()
    assert result["seed_count"] >= 30
    assert result["family_count"] >= 10
