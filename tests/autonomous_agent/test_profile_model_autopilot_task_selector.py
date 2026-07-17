"""Tests for the autopilot task selector / curiosity queue."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.task_selector import (
    build_curiosity_queue, all_tasks_bounded, morning_operator_review_present,
    source_followup_requires_policy,
)


def test_task_selector_consumes_research_seed_queue():
    tasks = build_curiosity_queue(max_tasks=10)
    assert any(t.research_seed_id for t in tasks)


def test_task_selector_builds_curiosity_queue():
    tasks = build_curiosity_queue(max_tasks=6)
    assert len(tasks) >= 2


def test_every_task_has_budget():
    for t in build_curiosity_queue(max_tasks=10):
        assert t.token_budget > 0
        assert t.wallclock_budget_seconds > 0


def test_every_task_has_completion_criteria():
    for t in build_curiosity_queue(max_tasks=10):
        assert len(t.completion_criteria) > 0


def test_source_followup_requires_source_policy():
    for t in build_curiosity_queue(max_tasks=20):
        assert source_followup_requires_policy(t) is True


def test_knowledge_promotion_requires_knowledge_policy():
    # No task promotes knowledge; all require operator review.
    for t in build_curiosity_queue(max_tasks=20):
        assert t.requires_operator_review is True


def test_no_unbounded_do_whatever_task():
    tasks = build_curiosity_queue(max_tasks=20)
    assert all_tasks_bounded(tasks)


def test_morning_operator_review_required():
    tasks = build_curiosity_queue(max_tasks=8)
    assert morning_operator_review_present(tasks)


def test_browsing_always_gated():
    for t in build_curiosity_queue(max_tasks=20):
        assert t.browsing_allowed is False


def test_max_tasks_bounded():
    tasks = build_curiosity_queue(max_tasks=5)
    # 5 seed tasks + 1 operator summary
    assert len(tasks) <= 6
