from __future__ import annotations

import os

import pytest

from hg_quantum.config import is_quantum2_enabled
from hg_quantum.production_shadow_runner import (
    SHADOW_FIRST_LIVE_ORDER,
    execute_shadow_first_live_flips,
    get_live_activation_summary,
    run_all_shadow_workloads,
    verify_live_module,
)


@pytest.fixture
def shadow_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(tmp_path / "corpus.sqlite3"))
    monkeypatch.setenv("Q2_PRODUCTION_SHADOW_BATCH_COUNT", "3")
    (tmp_path / "memory" / "overseer").mkdir(parents=True)
    os.environ["HG_QUANTUM_SYMMETRY_BREAKING_ENABLED"] = "true"
    os.environ["HG_QUANTUM_LDPC_VERIFICATION_ENABLED"] = "true"
    os.environ["HG_LEARNING_CONTROL_GROUP_ENABLED"] = "true"
    return tmp_path


def test_shadow_first_live_flips(shadow_workspace):
    run_all_shadow_workloads(workspace_root=shadow_workspace)
    result = execute_shadow_first_live_flips(
        workspace_root=shadow_workspace,
        run_shadow_batch=False,
    )
    assert result["ok"] is True, result
    for component in SHADOW_FIRST_LIVE_ORDER:
        assert is_quantum2_enabled(component, shadow_workspace) is True
    summary = get_live_activation_summary(shadow_workspace)
    for component in SHADOW_FIRST_LIVE_ORDER:
        assert component in summary["live_modules"]
    assert is_quantum2_enabled("mediator_registry", shadow_workspace) is False


def test_verify_live_modules_after_promotion(shadow_workspace):
    run_all_shadow_workloads(workspace_root=shadow_workspace)
    execute_shadow_first_live_flips(workspace_root=shadow_workspace, run_shadow_batch=False)
    for component in SHADOW_FIRST_LIVE_ORDER:
        check = verify_live_module(component, workspace_root=shadow_workspace)
        assert check["live_verified"] is True, check
