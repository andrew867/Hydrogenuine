"""Rule revocation."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.auto_approval_rules.receipts import write_rule_event_receipt
from hg_runtime.auto_approval_rules.schema import (
    AGENT0_ID,
    AutoApprovalRevocation,
    AutoApprovalRuleDecision,
    AutoApprovalRuleStatus,
)
from hg_runtime.auto_approval_rules.store import AutoApprovalRuleStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def revoke_rule(
    store: AutoApprovalRuleStore,
    rule_id: str,
    *,
    operator_ref: str,
    reason: str,
) -> AutoApprovalRevocation:
    if operator_ref == AGENT0_ID:
        raise ValueError("agent0 cannot revoke rules")
    rule = store.get_rule(rule_id)
    rule.status = AutoApprovalRuleStatus.REVOKED
    store.update_rule(rule)
    write_rule_event_receipt(
        store,
        rule,
        AutoApprovalRuleDecision.AUTO_APPROVE_REVOKED,
        reason,
        operator_ref=operator_ref,
        event="revoke",
    )
    return AutoApprovalRevocation(
        rule_id=rule_id,
        operator_ref=operator_ref,
        reason=reason,
        revoked_at=_now(),
    )


__all__ = ["revoke_rule"]
