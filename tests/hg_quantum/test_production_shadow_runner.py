from __future__ import annotations

import os

import pytest

from hg_quantum.config import is_quantum2_enabled
from hg_quantum.production_shadow_runner import (
    assess_go_no_go,
    execute_fingerprint_codec_live_flip,
    load_workload_fixtures,
    run_all_shadow_workloads,
    run_single_workload,
)


@pytest.fixture
def shadow_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_LEARNING_CORPUS_DB", str(tmp_path / "corpus.sqlite3"))
    monkeypatch.setenv("Q2_PRODUCTION_SHADOW_BATCH_COUNT", "3")
    (tmp_path / "memory" / "overseer").mkdir(parents=True)
    # Pre-own via monkeypatch (not raw os.environ[...]=) every quantum/learning
    # enable-flag the production shadow runner sets with os.environ.setdefault(...)
    # (production_shadow_runner.py). monkeypatch then owns them, the production
    # setdefault is a no-op, and teardown restores them. Raw/unowned writes leaked
    # to the next test on the same xdist worker and flipped tests/hg_quantum/
    # test_config.py::test_quantum_flags_default_off to fail (pipeline 89 straggler).
    monkeypatch.setenv("HG_QUANTUM_SYMMETRY_BREAKING_ENABLED", "true")
    monkeypatch.setenv("HG_QUANTUM_STATE_CORRELATION_ENABLED", "true")
    monkeypatch.setenv("HG_QUANTUM_LDPC_VERIFICATION_ENABLED", "true")
    monkeypatch.setenv("HG_QUANTUM_LDPC_VERIFICATION_SHADOW", "true")
    monkeypatch.setenv("HG_LEARNING_CONTROL_GROUP_ENABLED", "true")
    return tmp_path


def test_load_workload_fixtures():
    data = load_workload_fixtures()
    assert len(data["workloads"]) >= 3


def test_run_single_workload_records_shadow_events(shadow_workspace):
    wl = next(w for w in load_workload_fixtures()["workloads"] if w["id"] == "analytical_writing_4p")
    result = run_single_workload(wl, workspace_root=shadow_workspace)
    assert result["child_count"] == 4
    go = assess_go_no_go(shadow_workspace)
    assert go["shadow_summary"]["total_events"] >= 1


def test_run_all_shadow_workloads_and_go_no_go(shadow_workspace):
    batch = run_all_shadow_workloads(workspace_root=shadow_workspace)
    assert batch["ok"] is True
    assert len(batch["runs"]) >= 3
    go = assess_go_no_go(shadow_workspace)
    codec = next(a for a in go["assessments"] if a["component"] == "fingerprint_codec")
    assert codec["ready_for_live"] is True
    shell = next(a for a in go["assessments"] if a["component"] == "shell_model")
    assert shell["shadow_events"] >= 1
    mediator = next(a for a in go["assessments"] if a["component"] == "mediator_registry")
    assert mediator["ready_for_live"] is False


def test_fingerprint_codec_live_flip(shadow_workspace):
    run_all_shadow_workloads(workspace_root=shadow_workspace)
    flip = execute_fingerprint_codec_live_flip(workspace_root=shadow_workspace)
    assert flip["ok"] is True
    assert flip["codec_live"] is True
    assert is_quantum2_enabled("fingerprint_codec", shadow_workspace) is True
