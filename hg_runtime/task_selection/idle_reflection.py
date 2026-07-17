"""Idle reflection when no valid task exists."""

from __future__ import annotations

from dataclasses import dataclass

from hg_runtime.task_selection.schema import TaskSelectionVerdict, new_id, now_iso
from hg_runtime.task_selection.task_receipts import IdleReflectionReceipt, persist_idle_receipt


@dataclass
class IdleReflectionResult:
    receipt: IdleReflectionReceipt
    verdict: TaskSelectionVerdict
    reason_code: str


def perform_idle_reflection(*, universe_ref: str, reason_code: str = "no_valid_candidates") -> IdleReflectionResult:
    receipt = IdleReflectionReceipt(
        idle_reflection_receipt_id=new_id("idle-reflect"),
        universe_ref=universe_ref,
        reason_code=reason_code,
        created_at=now_iso(),
    ).with_hash()
    persist_idle_receipt(receipt)
    verdict = (
        TaskSelectionVerdict.YELLOW_OBJECTIVE_QUEUE_EMPTY
        if reason_code == "empty_queue"
        else TaskSelectionVerdict.GREEN_IDLE_REFLECTION
    )
    return IdleReflectionResult(receipt=receipt, verdict=verdict, reason_code=reason_code)
