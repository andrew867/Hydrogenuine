"""Governed work item tests."""
from __future__ import annotations

from hg_runtime.governed_work_loop.work_item import GovernedWorkItem, create_work_item


def test_work_item_hash():
    i = create_work_item(
        task_selection_ref="ts1",
        task_candidate_ref="c1",
        task_type="review_local_artifacts",
        scope_ref="internal:artifacts",
    )
    i2 = create_work_item(
        task_selection_ref="ts1",
        task_candidate_ref="c1",
        task_type="review_local_artifacts",
        scope_ref="internal:artifacts",
        work_type="review_local_artifacts",
    )
    assert i.work_type == "review_local_artifacts"
    assert i.hash
