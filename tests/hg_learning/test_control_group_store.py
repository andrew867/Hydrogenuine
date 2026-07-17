from __future__ import annotations

from pathlib import Path

import pytest

from hg_learning.feedback.control_group import ControlGroupStore
from hg_realtime.swarm.contracts import SwarmPlan
from hg_realtime.swarm.nodes import swarm_reduce, swarm_spawn


@pytest.fixture
def learning_db(tmp_path: Path, monkeypatch) -> Path:
    db = tmp_path / "learning.sqlite3"
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(db))
    return db


def test_swarm_reduce_records_control_group(learning_db: Path, monkeypatch):
    monkeypatch.setenv("HG_LEARNING_CONTROL_GROUP_ENABLED", "1")
    plan = SwarmPlan(summary="t", tasks=[{"workflow_id": "w1", "inputs": {}}], max_children=1)
    children = swarm_spawn(plan=plan, correlation_id="cg-record-1", learning_control_group=True)
    outputs = [{**children[0], "output": "ok"}]
    _, artifacts, _ = swarm_reduce(child_outputs=outputs)
    assert artifacts["learning_control_group"] is True
    store = ControlGroupStore(learning_db)
    stats = store.stats()
    assert stats["control_total"] >= 1


def test_control_group_store_stats(learning_db: Path):
    store = ControlGroupStore(learning_db)
    store.record_run(correlation_id="a", in_control_group=False, priors_enabled=True)
    store.record_run(correlation_id="b", in_control_group=True, priors_enabled=False)
    stats = store.stats()
    assert stats["treatment_total"] == 1
    assert stats["control_total"] == 1
