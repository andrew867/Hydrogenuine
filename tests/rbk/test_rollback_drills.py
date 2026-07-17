"""CT-07 RBK drill unit tests."""

from __future__ import annotations

import json

import pytest

from hg_core.admission.ingress import reset_controller
from hg_core.rollback.drills import (
    DRILL_RUNNERS,
    drill_d1_failed_srp_apply,
    drill_d7_dirty_worktree,
    drill_d8_rollback_failure_lockdown,
    refuse_dirty_rollback,
    run_all_drills,
)
from hg_core.rollback.harness import DrillHarness
from hg_srp.self_edit_policy import reset_self_edit_registries


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    reset_controller()
    reset_self_edit_registries()
    yield
    reset_controller()
    reset_self_edit_registries()


@pytest.fixture
def harness(tmp_path) -> DrillHarness:
    return DrillHarness(tmp_path)


def test_rbk_u1_harness_teardown_zero_residue(harness: DrillHarness) -> None:
    drill_dir = harness.repo_root / ".rbk_drill" / "tmp"
    drill_dir.mkdir(parents=True)
    (drill_dir / "x.txt").write_text("y", encoding="utf-8")
    assert harness.teardown() is True


def test_rbk_u2_drill_determinism(harness: DrillHarness) -> None:
    a = run_all_drills(DrillHarness(harness.repo_root))
    b = run_all_drills(DrillHarness(harness.repo_root))
    assert {k: v["verdict"] for k, v in a.items() if k.startswith("D")} == {
        k: v["verdict"] for k, v in b.items() if k.startswith("D")
    }


def test_rbk_d1_failed_srp_apply(harness: DrillHarness) -> None:
    outcome = drill_d1_failed_srp_apply(harness)
    assert outcome.ok
    assert outcome.drill_id == "D1"
    assert outcome.detail["master_unchanged"] is True


def test_rbk_d7_dirty_worktree_refuses(harness: DrillHarness) -> None:
    outcome = drill_d7_dirty_worktree(harness)
    assert outcome.ok
    assert outcome.reason_code == "rbk.refused.dirty_worktree"


def test_rbk_d8_lockdown_floor(harness: DrillHarness) -> None:
    outcome = drill_d8_rollback_failure_lockdown(harness)
    assert outcome.ok
    assert outcome.receipts[0].lockdown is True


def test_rbk_d7_refuse_dirty_helper(harness: DrillHarness) -> None:
    sandbox = harness.repo_root / "sandbox"
    sandbox.mkdir()
    dirty = sandbox / "dirty.txt"
    dirty.write_text("x", encoding="utf-8")
    ok, reason = refuse_dirty_rollback(sandbox, dirty_marker=dirty)
    assert not ok
    assert reason == "rbk.refused.dirty_worktree"
    assert (sandbox / "quarantine" / "dirty.txt").exists()


def test_rbk_all_drills_matrix(harness: DrillHarness) -> None:
    matrix = run_all_drills(harness)
    for drill_id in DRILL_RUNNERS:
        assert drill_id in matrix
        assert matrix[drill_id]["ok"] is True
    assert matrix["residue_free"] is True


def test_rbk_neg_unknown_drill_id_absent() -> None:
    assert "D11" not in DRILL_RUNNERS


def test_rbk_proof_receipts_emitted(harness: DrillHarness) -> None:
    matrix = run_all_drills(harness)
    for drill_id in ("D1", "D2", "D8"):
        assert matrix[drill_id]["receipts"]


def test_rbk_d6_replay_in_matrix(harness: DrillHarness) -> None:
    matrix = run_all_drills(harness)
    assert matrix["D6"]["ok"] is True


def test_rbk_d9_snapshot_restore(harness: DrillHarness) -> None:
    matrix = run_all_drills(harness)
    assert matrix["D9"]["ok"] is True
    manifest = json.loads((harness.snapshot_dir() / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "rbk_snapshot_v1"
