"""Task selection receipt tests."""
from __future__ import annotations

import pytest

from hg_runtime.task_selection.task_receipts import (
    IdleReflectionReceipt,
    TaskSelectionReceipt,
    TaskSwitchReceipt,
    persist_idle_receipt,
    persist_selection_receipt,
    persist_switch_receipt,
)


@pytest.fixture
def receipt_dir(tmp_path, monkeypatch):
    root = tmp_path / "ts"
    rdir = root / "receipts"
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.STORE_ROOT", root)
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.RECEIPT_DIR", rdir)
    return rdir


def test_selection_receipt_hash():
    r = TaskSelectionReceipt(
        task_selection_receipt_id="r1",
        decision_ref="d1",
        external_action_required=False,
        external_action_allowed=False,
        created_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    r2 = TaskSelectionReceipt(
        task_selection_receipt_id="r1",
        decision_ref="d1",
        external_action_required=False,
        external_action_allowed=False,
        created_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    assert r.hash == r2.hash


def test_switch_receipt_written(receipt_dir):
    sw = TaskSwitchReceipt(
        task_switch_receipt_id="sw1",
        from_task_ref="a",
        to_task_ref="b",
        decision_ref="d1",
        created_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    path = persist_switch_receipt(sw)
    assert path.is_file()


def test_idle_receipt_written(receipt_dir):
    idle = IdleReflectionReceipt(
        idle_reflection_receipt_id="idle1",
        universe_ref="u1",
        reason_code="empty_queue",
        created_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    path = persist_idle_receipt(idle)
    assert path.is_file()
