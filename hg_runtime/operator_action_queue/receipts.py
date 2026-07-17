"""Receipt writing for operator queue transitions."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.operator_action_queue.schema import (
    OperatorQueueDecisionType,
    OperatorQueueItem,
    OperatorQueueReceipt,
    new_queue_receipt_id,
)
from hg_runtime.operator_action_queue.store import OperatorQueueStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_transition_receipt(
    store: OperatorQueueStore,
    item: OperatorQueueItem,
    *,
    decision_type: OperatorQueueDecisionType,
    operator_ref: str | None,
    reason: str,
    previous_status: str,
    new_status: str,
    previous_receipt_ref: str | None = None,
) -> OperatorQueueReceipt:
    item.refresh_hash()
    receipt = OperatorQueueReceipt(
        receipt_id=new_queue_receipt_id(),
        queue_item_id=item.queue_item_id,
        action_id=item.action_id,
        action_type=item.action_type,
        decision_type=decision_type,
        operator_ref=operator_ref,
        reason=reason,
        created_at=_now_iso(),
        previous_status=previous_status,
        new_status=new_status,
        queue_hash_at_transition=item.queue_hash,
        previous_receipt_ref=previous_receipt_ref,
    )
    payload = receipt.to_payload()
    store.append_receipt(payload)
    return receipt


__all__ = ["write_transition_receipt"]
