"""Adapters for auto-approval rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hg_runtime.auto_approval_rules.evaluator import AutoApprovalEvaluator
from hg_runtime.auto_approval_rules.receipts import write_create_receipt
from hg_runtime.auto_approval_rules.schema import AutoApprovalRule
from hg_runtime.auto_approval_rules.store import AutoApprovalRuleStore
from hg_runtime.operator_action_queue.queue import OperatorQueueRuntime


def create_readonly_fixture_rule(
    store: AutoApprovalRuleStore,
    *,
    action_type: str = "status_refresh",
    operator_ref: str = "local-operator",
    hours: int = 24,
) -> AutoApprovalRule:
    rule = store.create_rule(
        title=f"Fixture {action_type}",
        description="Read-only fixture rule for Phase 3",
        action_type=action_type,
        allowed_surfaces=["exciton", "proof", "operator"],
        max_risk_class="read_only",
        created_by_operator_ref=operator_ref,
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(),
        max_count_per_run=5,
        dry_run_only=False,
    )
    write_create_receipt(store, rule, operator_ref)
    return rule


def evaluate_queue_item(
    store: AutoApprovalRuleStore,
    queue: OperatorQueueRuntime,
    queue_item_id: str,
    *,
    workspace=None,
) -> dict:
    item = queue.get_item(queue_item_id)
    if not item:
        return {"ok": False, "error": "item_not_found"}
    ev = AutoApprovalEvaluator(store, workspace=workspace).evaluate_for_queue_item(item)
    return {"ok": True, "evaluation": ev.to_payload()}


__all__ = ["create_readonly_fixture_rule", "evaluate_queue_item"]
