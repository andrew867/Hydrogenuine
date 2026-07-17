from __future__ import annotations

import os

import pytest

from hg_quantum.production_shadow_runner import execute_full_q2_live_activation, run_all_shadow_workloads
from hg_quantum.production_validation import (
    assert_post_live_ready,
    assess_post_live_divergence,
    load_validation_fixtures,
    run_all_validation_workloads,
)


@pytest.fixture
def validation_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(tmp_path / "corpus.sqlite3"))
    monkeypatch.setenv("Q2_PRODUCTION_SHADOW_BATCH_COUNT", "3")
    monkeypatch.setenv("Q2_PRODUCTION_VALIDATION_BATCH_COUNT", "12")
    (tmp_path / "memory" / "overseer").mkdir(parents=True)
    os.environ["HG_QUANTUM_SYMMETRY_BREAKING_ENABLED"] = "true"
    os.environ["HG_QUANTUM_LDPC_VERIFICATION_ENABLED"] = "true"
    os.environ["HG_LEARNING_CONTROL_GROUP_ENABLED"] = "true"
    return tmp_path


def test_load_validation_fixtures():
    data = load_validation_fixtures()
    assert len(data["workloads"]) >= 3


def test_assert_post_live_ready_blocks_without_live(validation_workspace):
    ready = assert_post_live_ready(validation_workspace)
    assert ready["ok"] is False
    assert ready["missing"]


def test_production_validation_after_live_activation(validation_workspace):
    run_all_shadow_workloads(workspace_root=validation_workspace)
    live = execute_full_q2_live_activation(workspace_root=validation_workspace)
    assert live.get("ok") is True
    ready = assert_post_live_ready(validation_workspace)
    assert ready["ok"] is True
    batch = run_all_validation_workloads(workspace_root=validation_workspace)
    assert batch.get("ok") is True, batch
    report = assess_post_live_divergence(validation_workspace)
    assert report["ok"] is True
    assert any(c["name"] == "control_group_control_present" and c["pass"] for c in report["checks"])
