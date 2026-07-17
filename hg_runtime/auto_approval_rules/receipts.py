"""Auto-approval receipts."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.auto_approval_rules.schema import (
    AutoApprovalEvaluation,
    AutoApprovalRule,
    AutoApprovalRuleDecision,
    AutoApprovalRuleReceipt,
    new_receipt_id,
)
from hg_runtime.auto_approval_rules.store import AutoApprovalRuleStore
from hg_runtime.operator_action_queue.schema import OperatorQueueItem


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_rule_event_receipt(
    store: AutoApprovalRuleStore,
    rule: AutoApprovalRule,
    decision: AutoApprovalRuleDecision,
    reason: str,
    *,
    operator_ref: str | None = None,
    event: str = "rule_event",
) -> AutoApprovalRuleReceipt:
    receipt = AutoApprovalRuleReceipt(
        receipt_id=new_receipt_id(),
        rule_id=rule.rule_id,
        event=event,
        decision=decision,
        reason=reason,
        created_at=_now(),
        operator_ref=operator_ref,
    )
    store.append_receipt(receipt)
    return receipt


def write_evaluation_receipt(
    store: AutoApprovalRuleStore,
    rule: AutoApprovalRule,
    item: OperatorQueueItem,
    evaluation: AutoApprovalEvaluation,
) -> AutoApprovalRuleReceipt:
    receipt = AutoApprovalRuleReceipt(
        receipt_id=new_receipt_id(),
        rule_id=rule.rule_id,
        event="evaluate",
        decision=evaluation.decision,
        reason=evaluation.reason,
        created_at=_now(),
        queue_item_id=item.queue_item_id,
    )
    store.append_receipt(receipt)
    return receipt


def write_create_receipt(
    store: AutoApprovalRuleStore,
    rule: AutoApprovalRule,
    operator_ref: str,
) -> AutoApprovalRuleReceipt:
    return write_rule_event_receipt(
        store,
        rule,
        AutoApprovalRuleDecision.AUTO_APPROVE_ALLOWED,
        "rule created",
        operator_ref=operator_ref,
        event="create",
    )


__all__ = ["write_create_receipt", "write_evaluation_receipt", "write_rule_event_receipt"]
