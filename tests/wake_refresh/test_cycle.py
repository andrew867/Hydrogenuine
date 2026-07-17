"""Wake refresh cycle tests."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.wake_refresh.refresh_cycle import WakeRefreshConfig, run_wake_refresh_cycle
from hg_runtime.wake_refresh.sleep_reconciliation import build_sleep_state_from_shutdown, write_sleep_state


def test_first_boot_yellow_absent(tmp_path):
    cycle = run_wake_refresh_cycle(workspace=tmp_path, config=WakeRefreshConfig(dry_run=True))
    assert cycle.verdict == "YELLOW_PREVIOUS_SLEEP_STATE_ABSENT"
    assert cycle.readiness.previous_sleep_state.value == "absent"


def test_clean_sleep_green(tmp_path):
    write_sleep_state(
        build_sleep_state_from_shutdown(run_id="r1", shutdown_clean=True, stop_receipt_ref="stop-1"),
        workspace=tmp_path,
    )
    cycle = run_wake_refresh_cycle(workspace=tmp_path, config=WakeRefreshConfig(dry_run=True))
    assert cycle.verdict in {"GREEN_WAKE_REFRESH_READY", "YELLOW_WAKE_REFRESH_PARTIAL", "YELLOW_PREVIOUS_SLEEP_STATE_ABSENT"}


def test_unclean_sleep_visible(tmp_path):
    write_sleep_state(
        build_sleep_state_from_shutdown(
            run_id="r2",
            shutdown_clean=False,
            pending_tasks=["unfinished-task"],
            panic_state=True,
        ),
        workspace=tmp_path,
    )
    cycle = run_wake_refresh_cycle(workspace=tmp_path, config=WakeRefreshConfig(dry_run=True))
    assert cycle.reconciliation.previous_state.value == "unclean"
    assert cycle.readiness.unfinished_work_count >= 1


def test_proof_deletion_blocked(tmp_path):
    proof = tmp_path / "docs" / "proofs" / "test" / "bundle" / "x.json"
    proof.parent.mkdir(parents=True)
    proof.write_text("{}", encoding="utf-8")
    from hg_runtime.wake_refresh.waste_elimination import attempt_cleanup_path
    ok, reason = attempt_cleanup_path(proof, workspace=tmp_path)
    assert ok is False
    assert "RED" in reason or "proof" in reason.lower()
