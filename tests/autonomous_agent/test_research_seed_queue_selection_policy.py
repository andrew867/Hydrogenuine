"""Tests for the research seed queue selection policy."""

from __future__ import annotations

import pytest

from hg_runtime.overnight_qa.research_seed_queue import (
    zero_rank_seeds, runtime_select, selection_policy_snapshot,
    incomplete_queue_is_failure,
)


def test_zero_seed_ranking_is_advisory():
    rankings = zero_rank_seeds(["observer_state_frequency_hypothesis", "schumann_thz_mantissa_bridge"])
    for r in rankings:
        assert r.advisory_only is True
        assert r.chosen_by_zero is True
        assert r.approved_by_runtime is False


def test_runtime_approval_required_for_selection():
    ranking = zero_rank_seeds(["observer_state_frequency_hypothesis"])[0]
    approved = runtime_select(ranking, approve=True)
    assert approved.runtime_approved is True
    denied = runtime_select(ranking, approve=False)
    assert denied.runtime_approved is False


def test_incomplete_queue_not_failure():
    assert incomplete_queue_is_failure(approved_count=2, total=32) is False
    snap = selection_policy_snapshot()
    assert snap["incomplete_queue_is_not_failure"] is True


def test_skipped_seed_recorded_honestly():
    ranking = zero_rank_seeds(["schumann_thz_mantissa_bridge"])[0]
    decision = runtime_select(ranking, approve=False)
    assert decision.decision == "skipped"
    assert decision.skipped_not_failed is True


def test_selected_seed_requires_budget():
    ranking = zero_rank_seeds(["subjective_time_experiment_design"])[0]
    decision = runtime_select(ranking, approve=True, budget="medium")
    assert decision.budget == "medium"


def test_selected_seed_requires_completion_criteria():
    ranking = zero_rank_seeds(["subjective_time_experiment_design"])[0]
    decision = runtime_select(ranking, approve=True)
    assert len(decision.completion_criteria) > 0


def test_browsing_seed_requires_source_policy():
    from hg_runtime.overnight_qa.research_seeds import build_research_seeds
    for s in build_research_seeds():
        if s.can_browse_later:
            assert s.source_policy_required is True


def test_promotion_requires_knowledge_policy():
    from hg_runtime.overnight_qa.research_seeds import build_research_seeds
    for s in build_research_seeds():
        assert s.knowledge_policy_required is True


def test_operator_override_beats_zero_ranking():
    ranking = zero_rank_seeds(["observer_state_frequency_hypothesis"])[0]
    decision = runtime_select(ranking, approve=True, operator_override=True)
    assert decision.runtime_approved is False
    assert "operator" in decision.reason.lower()


def test_chosen_by_zero_not_approved_by_runtime():
    snap = selection_policy_snapshot()
    assert snap["chosen_by_zero_is_not_approved_by_runtime"] is True
