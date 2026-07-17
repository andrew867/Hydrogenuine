"""Decision recording helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.exciton_action_model.policy_refs import OperatorDecisionRef
from hg_runtime.exciton_action_model.status import AgentActionStatus
from hg_runtime.operator_action_queue.errors import (
    InvalidTransitionError,
    ItemNotFoundError,
    NotExecutableError,
    SelfApprovalError,
    StopPanicActiveError,
)
from hg_runtime.operator_action_queue.policy import (
    item_may_be_approved,
    item_may_mark_executed,
    may_transition,
)
from hg_runtime.operator_action_queue.receipts import write_transition_receipt
from hg_runtime.operator_action_queue.schema import (
    OperatorQueueDecision,
    OperatorQueueDecisionType,
    OperatorQueueItem,
    new_queue_item_id,
)
from hg_runtime.operator_action_queue.stop_panic_policy import StopPanicState
from hg_runtime.operator_action_queue.store import OperatorQueueStore

AGENT0_ID = "agent0"
_HIDDEN_MARKERS = ("chain_of_thought", "hidden_reasoning", "internal_scratch", "<think>")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scrub_text(text: str) -> str:
    out = text
    for marker in _HIDDEN_MARKERS:
        if marker.lower() in out.lower():
            out = out.replace(marker, "[redacted]")
    return out


def _find_item(queue_items: list[OperatorQueueItem], queue_item_id: str) -> OperatorQueueItem:
    for item in queue_items:
        if item.queue_item_id == queue_item_id:
            return item
    raise ItemNotFoundError(queue_item_id)


def _transition(
    store: OperatorQueueStore,
    items: list[OperatorQueueItem],
    queue_item_id: str,
    new_status: AgentActionStatus,
    decision_type: OperatorQueueDecisionType,
    *,
    operator_ref: str | None,
    reason: str,
    stop_panic: StopPanicState,
    block_on_stop_for_approval: bool = False,
) -> tuple[OperatorQueueItem, OperatorQueueDecision]:
    item = _find_item(items, queue_item_id)
    prev = item.status.value

    if block_on_stop_for_approval and stop_panic.blocks_approval():
        raise StopPanicActiveError("stop_or_panic_active")

    if not may_transition(item.status, new_status):
        raise InvalidTransitionError(f"{prev} -> {new_status.value}")

    item.status = new_status
    item.refresh_hash()

    if operator_ref and decision_type in (
        OperatorQueueDecisionType.APPROVE_ITEM,
        OperatorQueueDecisionType.DENY_ITEM,
        OperatorQueueDecisionType.CANCEL_ITEM,
    ):
        item.action_request.operator_decision_ref = OperatorDecisionRef(
            decision_id=new_queue_item_id(),
            operator_ref=operator_ref,
            decision_kind=decision_type.value,
            created_at=_now_iso(),
        )

    receipt = write_transition_receipt(
        store,
        item,
        decision_type=decision_type,
        operator_ref=operator_ref,
        reason=_scrub_text(reason),
        previous_status=prev,
        new_status=new_status.value,
    )

    decision = OperatorQueueDecision(
        decision_id=receipt.receipt_id,
        queue_item_id=item.queue_item_id,
        decision_type=decision_type,
        operator_ref=operator_ref,
        reason=_scrub_text(reason),
        created_at=receipt.created_at,
        previous_status=prev,
        new_status=new_status.value,
    )
    return item, decision


def approve_item(
    store: OperatorQueueStore,
    items: list[OperatorQueueItem],
    queue_item_id: str,
    *,
    operator_ref: str,
    reason: str = "operator_approved",
    stop_panic: StopPanicState,
) -> tuple[OperatorQueueItem, OperatorQueueDecision]:
    if operator_ref == AGENT0_ID:
        raise SelfApprovalError("agent0 cannot approve queue items")
    item = _find_item(items, queue_item_id)
    ok, msg = item_may_be_approved(item, stop_panic=stop_panic.blocks_approval())
    if not ok:
        if msg == "stop_or_panic_active":
            raise StopPanicActiveError(msg)
        raise InvalidTransitionError(msg)
    return _transition(
        store,
        items,
        queue_item_id,
        AgentActionStatus.APPROVED,
        OperatorQueueDecisionType.APPROVE_ITEM,
        operator_ref=operator_ref,
        reason=reason,
        stop_panic=stop_panic,
        block_on_stop_for_approval=True,
    )


def deny_item(
    store: OperatorQueueStore,
    items: list[OperatorQueueItem],
    queue_item_id: str,
    *,
    operator_ref: str,
    reason: str,
    stop_panic: StopPanicState,
) -> tuple[OperatorQueueItem, OperatorQueueDecision]:
    return _transition(
        store,
        items,
        queue_item_id,
        AgentActionStatus.DENIED,
        OperatorQueueDecisionType.DENY_ITEM,
        operator_ref=operator_ref,
        reason=reason,
        stop_panic=stop_panic,
    )


def expire_item(
    store: OperatorQueueStore,
    items: list[OperatorQueueItem],
    queue_item_id: str,
    *,
    reason: str,
    stop_panic: StopPanicState,
) -> tuple[OperatorQueueItem, OperatorQueueDecision]:
    return _transition(
        store,
        items,
        queue_item_id,
        AgentActionStatus.EXPIRED,
        OperatorQueueDecisionType.EXPIRE_ITEM,
        operator_ref=None,
        reason=reason,
        stop_panic=stop_panic,
    )


def cancel_item(
    store: OperatorQueueStore,
    items: list[OperatorQueueItem],
    queue_item_id: str,
    *,
    operator_ref: str,
    reason: str,
    stop_panic: StopPanicState,
) -> tuple[OperatorQueueItem, OperatorQueueDecision]:
    return _transition(
        store,
        items,
        queue_item_id,
        AgentActionStatus.CANCELLED,
        OperatorQueueDecisionType.CANCEL_ITEM,
        operator_ref=operator_ref,
        reason=reason,
        stop_panic=stop_panic,
    )


def block_item(
    store: OperatorQueueStore,
    items: list[OperatorQueueItem],
    queue_item_id: str,
    *,
    reason: str,
    stop_panic: StopPanicState,
) -> tuple[OperatorQueueItem, OperatorQueueDecision]:
    return _transition(
        store,
        items,
        queue_item_id,
        AgentActionStatus.BLOCKED,
        OperatorQueueDecisionType.BLOCK_ITEM,
        operator_ref=None,
        reason=reason,
        stop_panic=stop_panic,
    )


def mark_executed(
    store: OperatorQueueStore,
    items: list[OperatorQueueItem],
    queue_item_id: str,
    *,
    execution_receipt_ref: str,
    dry_run: bool = False,
    stop_panic: StopPanicState,
) -> tuple[OperatorQueueItem, OperatorQueueDecision]:
    from hg_runtime.operator_action_queue.policy import item_execution_eligible

    item = _find_item(items, queue_item_id)
    ok, msg = item_may_mark_executed(item, dry_run=dry_run)
    if not ok:
        raise NotExecutableError(msg)
    exec_ok, exec_msg = item_execution_eligible(
        item,
        stop_panic=stop_panic.blocks_execution(),
        dry_run=dry_run,
    )
    if not exec_ok:
        raise NotExecutableError(exec_msg)

    item, decision = _transition(
        store,
        items,
        queue_item_id,
        AgentActionStatus.EXECUTED,
        OperatorQueueDecisionType.MARK_EXECUTED,
        operator_ref=None,
        reason=f"marked_executed:{execution_receipt_ref}",
        stop_panic=stop_panic,
    )
    item.action_request.execution_receipt_ref = execution_receipt_ref
    item.refresh_hash()
    return item, decision


def mark_failed(
    store: OperatorQueueStore,
    items: list[OperatorQueueItem],
    queue_item_id: str,
    *,
    reason: str,
    stop_panic: StopPanicState,
) -> tuple[OperatorQueueItem, OperatorQueueDecision]:
    return _transition(
        store,
        items,
        queue_item_id,
        AgentActionStatus.FAILED,
        OperatorQueueDecisionType.MARK_FAILED,
        operator_ref=None,
        reason=reason,
        stop_panic=stop_panic,
    )


__all__ = [
    "approve_item",
    "block_item",
    "cancel_item",
    "deny_item",
    "expire_item",
    "mark_executed",
    "mark_failed",
]
