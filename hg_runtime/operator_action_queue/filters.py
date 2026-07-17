"""Queue item filtering helpers."""

from __future__ import annotations

from hg_runtime.exciton_action_model.status import AgentActionStatus
from hg_runtime.operator_action_queue.policy import item_execution_eligible
from hg_runtime.operator_action_queue.schema import OperatorQueueFilter, OperatorQueueItem


def apply_filter(items: list[OperatorQueueItem], filt: OperatorQueueFilter | None) -> list[OperatorQueueItem]:
    if filt is None:
        return list(items)
    return [i for i in items if filt.matches(i)]


def pending_items(items: list[OperatorQueueItem]) -> list[OperatorQueueItem]:
    return [i for i in items if i.status == AgentActionStatus.QUEUED]


def approved_items(items: list[OperatorQueueItem]) -> list[OperatorQueueItem]:
    return [i for i in items if i.status == AgentActionStatus.APPROVED]


def denied_items(items: list[OperatorQueueItem]) -> list[OperatorQueueItem]:
    return [i for i in items if i.status == AgentActionStatus.DENIED]


def actionable_items(
    items: list[OperatorQueueItem],
    *,
    stop_panic: bool = False,
) -> list[OperatorQueueItem]:
    return [i for i in pending_items(items) if i.status == AgentActionStatus.QUEUED]


def approved_eligible_items(
    items: list[OperatorQueueItem],
    *,
    stop_panic: bool = False,
) -> list[OperatorQueueItem]:
    result: list[OperatorQueueItem] = []
    for item in approved_items(items):
        ok, _ = item_execution_eligible(item, stop_panic=stop_panic)
        if ok:
            result.append(item)
    return result


__all__ = [
    "actionable_items",
    "apply_filter",
    "approved_eligible_items",
    "approved_items",
    "denied_items",
    "pending_items",
]
