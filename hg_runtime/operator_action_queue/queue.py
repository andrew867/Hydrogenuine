"""Unified operator action queue runtime — records requests, never executes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.exciton_action_model.schema import AgentActionRequest
from hg_runtime.exciton_action_model.status import AgentActionStatus
from hg_runtime.operator_action_queue import decisions
from hg_runtime.operator_action_queue.errors import SecretLeakError
from hg_runtime.operator_action_queue.filters import (
    actionable_items,
    apply_filter,
    approved_eligible_items,
    approved_items,
    denied_items,
    pending_items,
)
from hg_runtime.operator_action_queue.policy import item_execution_eligible
from hg_runtime.operator_action_queue.receipts import write_transition_receipt
from hg_runtime.operator_action_queue.schema import (
    OperatorActionQueue,
    OperatorQueueDecision,
    OperatorQueueDecisionType,
    OperatorQueueFilter,
    OperatorQueueItem,
    OperatorQueueStats,
    OperatorQueueSummary,
    new_queue_item_id,
)
from hg_runtime.operator_action_queue.stop_panic_policy import StopPanicState, load_stop_panic_state
from hg_runtime.operator_action_queue.store import OperatorQueueStore

_HIDDEN_MARKERS = ("chain_of_thought", "hidden_reasoning", "internal_scratch")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scrub_preview(text: str) -> str:
    out = text
    for marker in _HIDDEN_MARKERS:
        if marker in out.lower():
            out = out.replace(marker, "[redacted]")
    return out[:2000]


class OperatorQueueRuntime:
    """General-purpose operator action queue. Does not execute or grant authority."""

    def __init__(
        self,
        store: OperatorQueueStore,
        *,
        run_dir: Path | None = None,
        workspace: Path | None = None,
    ) -> None:
        self.store = store
        self.run_dir = run_dir
        self.workspace = workspace
        self._queue = self.store.load()
        self._stop_panic = load_stop_panic_state(workspace=workspace, run_dir=run_dir)

    def reload(self) -> None:
        self._queue = self.store.load()
        self._stop_panic = load_stop_panic_state(workspace=self.workspace, run_dir=self.run_dir)

    def stop_panic_state(self) -> StopPanicState:
        return self._stop_panic

    def _save(self) -> None:
        self.store.save(self._queue)

    def _validate_item(self, item: OperatorQueueItem) -> None:
        payload = item.to_payload()
        forbidden = scan_forbidden(payload)
        if forbidden:
            raise SecretLeakError(str(forbidden[:5]))

    def enqueue(self, action_request: AgentActionRequest) -> OperatorQueueItem:
        action_request.human_summary = _scrub_preview(action_request.human_summary)
        action_request.sanitized_preview = _scrub_preview(action_request.sanitized_preview)
        if action_request.status not in (
            AgentActionStatus.QUEUED,
            AgentActionStatus.DRY_RUN_ONLY,
        ):
            action_request.status = AgentActionStatus.QUEUED
        action_request.item_hash = action_request.to_payload()["item_hash"]

        item = OperatorQueueItem(
            queue_item_id=new_queue_item_id(),
            action_request=action_request,
        )
        item.refresh_hash()
        self._validate_item(item)
        self._queue.items.append(item)
        write_transition_receipt(
            self.store,
            item,
            decision_type=OperatorQueueDecisionType.ENQUEUE_ITEM,
            operator_ref=None,
            reason="enqueued",
            previous_status="",
            new_status=item.status.value,
        )
        self._save()
        return item

    def list_items(self, filt: OperatorQueueFilter | None = None) -> list[OperatorQueueItem]:
        return apply_filter(self._queue.items, filt)

    def get_item(self, queue_item_id: str) -> OperatorQueueItem | None:
        for item in self._queue.items:
            if item.queue_item_id == queue_item_id:
                return item
        return None

    def find_by_action_id(self, action_id: str) -> OperatorQueueItem | None:
        for item in self._queue.items:
            if item.action_id == action_id:
                return item
        return None

    def approve_item(
        self,
        queue_item_id: str,
        operator_ref: str,
        reason: str = "operator_approved",
    ) -> OperatorQueueDecision:
        _, decision = decisions.approve_item(
            self.store,
            self._queue.items,
            queue_item_id,
            operator_ref=operator_ref,
            reason=reason,
            stop_panic=self._stop_panic,
        )
        self._save()
        return decision

    def deny_item(
        self,
        queue_item_id: str,
        operator_ref: str,
        reason: str,
    ) -> OperatorQueueDecision:
        _, decision = decisions.deny_item(
            self.store,
            self._queue.items,
            queue_item_id,
            operator_ref=operator_ref,
            reason=reason,
            stop_panic=self._stop_panic,
        )
        self._save()
        return decision

    def expire_item(self, queue_item_id: str, reason: str) -> OperatorQueueDecision:
        _, decision = decisions.expire_item(
            self.store,
            self._queue.items,
            queue_item_id,
            reason=reason,
            stop_panic=self._stop_panic,
        )
        self._save()
        return decision

    def cancel_item(
        self,
        queue_item_id: str,
        operator_ref: str,
        reason: str,
    ) -> OperatorQueueDecision:
        _, decision = decisions.cancel_item(
            self.store,
            self._queue.items,
            queue_item_id,
            operator_ref=operator_ref,
            reason=reason,
            stop_panic=self._stop_panic,
        )
        self._save()
        return decision

    def mark_executed(
        self,
        queue_item_id: str,
        execution_receipt_ref: str,
        *,
        dry_run: bool = False,
    ) -> OperatorQueueDecision:
        _, decision = decisions.mark_executed(
            self.store,
            self._queue.items,
            queue_item_id,
            execution_receipt_ref=execution_receipt_ref,
            dry_run=dry_run,
            stop_panic=self._stop_panic,
        )
        self._save()
        return decision

    def mark_failed(self, queue_item_id: str, reason: str) -> OperatorQueueDecision:
        _, decision = decisions.mark_failed(
            self.store,
            self._queue.items,
            queue_item_id,
            reason=reason,
            stop_panic=self._stop_panic,
        )
        self._save()
        return decision

    def block_item(self, queue_item_id: str, reason: str) -> OperatorQueueDecision:
        _, decision = decisions.block_item(
            self.store,
            self._queue.items,
            queue_item_id,
            reason=reason,
            stop_panic=self._stop_panic,
        )
        self._save()
        return decision

    def _stats(self) -> OperatorQueueStats:
        stats = OperatorQueueStats(total=len(self._queue.items))
        for item in self._queue.items:
            match item.status:
                case AgentActionStatus.QUEUED:
                    stats.queued += 1
                case AgentActionStatus.APPROVED:
                    stats.approved += 1
                case AgentActionStatus.DENIED:
                    stats.denied += 1
                case AgentActionStatus.EXPIRED:
                    stats.expired += 1
                case AgentActionStatus.CANCELLED:
                    stats.cancelled += 1
                case AgentActionStatus.EXECUTED:
                    stats.executed += 1
                case AgentActionStatus.FAILED:
                    stats.failed += 1
                case AgentActionStatus.INVALID:
                    stats.invalid += 1
                case AgentActionStatus.BLOCKED:
                    stats.blocked += 1
                case AgentActionStatus.DRY_RUN_ONLY:
                    stats.dry_run_only += 1
        return stats

    def summarize(self) -> OperatorQueueSummary:
        sp = self._stop_panic
        return OperatorQueueSummary(
            stats=self._stats(),
            queue_path=str(self.store.queue_path),
            receipts_path=str(self.store.receipts_path),
            stop_active=sp.stop_active,
            panic_active=sp.panic_active,
            emergency_lock=sp.emergency_lock,
            degraded_mode=sp.degraded_mode,
        )

    def pending_count(self) -> int:
        return len(pending_items(self._queue.items))

    def approved_count(self) -> int:
        return len(approved_items(self._queue.items))

    def denied_count(self) -> int:
        return len(denied_items(self._queue.items))

    def actionable_items(self) -> list[OperatorQueueItem]:
        return actionable_items(self._queue.items, stop_panic=self._stop_panic.blocks_approval())

    def approved_eligible_items(self) -> list[OperatorQueueItem]:
        return approved_eligible_items(
            self._queue.items,
            stop_panic=self._stop_panic.blocks_execution(),
        )

    def item_execution_eligible(self, queue_item_id: str) -> tuple[bool, str]:
        item = self.get_item(queue_item_id)
        if not item:
            return False, "not_found"
        return item_execution_eligible(
            item,
            stop_panic=self._stop_panic.blocks_execution(),
        )


def open_default_queue(workspace: Path | None = None) -> OperatorQueueRuntime:
    store = OperatorQueueStore.default(workspace)
    return OperatorQueueRuntime(store, workspace=workspace)


def open_run_queue(run_dir: Path) -> OperatorQueueRuntime:
    store = OperatorQueueStore.for_run(run_dir)
    return OperatorQueueRuntime(store, run_dir=run_dir)


__all__ = [
    "OperatorQueueRuntime",
    "open_default_queue",
    "open_run_queue",
]
