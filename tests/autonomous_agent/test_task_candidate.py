"""Task candidate tests."""
from __future__ import annotations

from hg_runtime.task_selection.task_candidate import TaskCandidate, create_candidate
import pytest


def test_candidate_hash_deterministic():
    c = TaskCandidate(
        task_candidate_id="c1",
        objective_scope_ref="internal:artifacts",
        task_type="review_local_artifacts",
        title="t",
        risk_class="low",
        requires_external_action=False,
        requires_operator_review=False,
        status="candidate",
        created_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    c2 = TaskCandidate(
        task_candidate_id="c1",
        objective_scope_ref="internal:artifacts",
        task_type="review_local_artifacts",
        title="t",
        risk_class="low",
        requires_external_action=False,
        requires_operator_review=False,
        status="candidate",
        created_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    assert c.hash == c2.hash


def test_candidate_requires_objective_scope():
    with pytest.raises(ValueError):
        create_candidate(objective_scope="", task_type="review_local_artifacts")
