"""Sleep reconciliation tests."""

from __future__ import annotations

from hg_runtime.wake_refresh.schema import PreviousSleepState
from hg_runtime.wake_refresh.sleep_reconciliation import reconcile_on_wake


def test_absent_sleep_state():
    r = reconcile_on_wake(None)
    assert r.previous_state == PreviousSleepState.ABSENT


def test_clean_sleep():
    r = reconcile_on_wake({"shutdown_clean": True, "stop_receipt_ref": "x", "pending_tasks": []})
    assert r.previous_state == PreviousSleepState.CLEAN


def test_unclean_sleep():
    r = reconcile_on_wake({"shutdown_clean": False, "pending_tasks": ["t1"], "panic_state": False})
    assert r.previous_state == PreviousSleepState.UNCLEAN
    assert len(r.unfinished_items) >= 1
