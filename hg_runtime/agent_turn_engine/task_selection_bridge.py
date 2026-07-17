"""Bridge task selection refs onto agent turn receipts."""

from __future__ import annotations

from typing import Any

from hg_runtime.task_selection.task_selector import TaskSelectionResult, attach_task_selection_to_turn_payload


def enrich_turn_receipt_payload(payload: dict[str, Any], task_result: TaskSelectionResult) -> dict[str, Any]:
    return attach_task_selection_to_turn_payload(payload, task_result)


__all__ = ["enrich_turn_receipt_payload"]
