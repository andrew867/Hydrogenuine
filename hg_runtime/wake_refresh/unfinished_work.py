"""Unfinished work classification."""

from __future__ import annotations

from hg_runtime.wake_refresh.schema import (
    SleepReconciliation,
    UnfinishedWorkClassification,
    UnfinishedWorkItem,
)


def classify_unfinished(reconciliation: SleepReconciliation) -> list[UnfinishedWorkItem]:
    return list(reconciliation.unfinished_items)


def count_requires_review(items: list[UnfinishedWorkItem]) -> int:
    review_classes = {
        UnfinishedWorkClassification.INTERRUPTED_NEEDS_REVIEW,
        UnfinishedWorkClassification.UNKNOWN_NEEDS_REVIEW,
        UnfinishedWorkClassification.BLOCKING_WAKE,
        UnfinishedWorkClassification.DO_NOT_RETRY_WITHOUT_OPERATOR,
    }
    return sum(1 for i in items if i.classification in review_classes)


def dropped_unfinished(items_before: list[UnfinishedWorkItem], items_after: list[UnfinishedWorkItem]) -> bool:
    before_ids = {i.item_id for i in items_before}
    after_ids = {i.item_id for i in items_after}
    return bool(before_ids - after_ids)


__all__ = ["classify_unfinished", "count_requires_review", "dropped_unfinished"]
