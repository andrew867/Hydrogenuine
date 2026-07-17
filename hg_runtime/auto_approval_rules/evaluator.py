"""Auto-approval evaluator — policy only, does not execute."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.operator_action_queue.schema import OperatorQueueItem
from hg_runtime.operator_action_queue.stop_panic_policy import load_stop_panic_state
from hg_runtime.auto_approval_rules.policy import is_forbidden_rule_action_type, risk_within_ceiling
from hg_runtime.auto_approval_rules.receipts import write_evaluation_receipt, write_rule_event_receipt
from hg_runtime.auto_approval_rules.schema import (
    AutoApprovalEvaluation,
    AutoApprovalRule,
    AutoApprovalRuleDecision,
    AutoApprovalRuleStatus,
)
from hg_runtime.auto_approval_rules.store import AutoApprovalRuleStore
from hg_runtime.exciton.chrono_expiry import deny_auto_approval_if_clock_uncertain

WORKSPACE = __import__("pathlib").Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_expiry(expires_at: str) -> bool:
    try:
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= exp
    except ValueError:
        return True


class AutoApprovalEvaluator:
    def __init__(self, store: AutoApprovalRuleStore, *, workspace=None) -> None:
        self.store = store
        self.workspace = workspace or WORKSPACE

    def evaluate_for_queue_item(
        self,
        item: OperatorQueueItem,
        *,
        domain: str | None = None,
    ) -> AutoApprovalEvaluation:
        sp = load_stop_panic_state(self.workspace)
        if sp.panic_active:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_PANIC_BLOCKED,
                "panic active",
            )
        ok_clock, clock_reason = deny_auto_approval_if_clock_uncertain(
            getattr(item.action_request, "time_confidence", None)
        )
        if not ok_clock:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_DENIED,
                clock_reason,
            )
        if sp.stop_active:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_STOP_BLOCKED,
                "stop active",
            )

        action_type = item.action_type
        if is_forbidden_rule_action_type(action_type):
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_DENIED,
                "action type not auto-approvable",
            )

        rules = [r for r in self.store.load_rules() if r.status == AutoApprovalRuleStatus.ACTIVE]
        for rule in rules:
            result = self._evaluate_rule(rule, item, domain=domain)
            if result.decision == AutoApprovalRuleDecision.AUTO_APPROVE_ALLOWED:
                receipt = write_evaluation_receipt(self.store, rule, item, result)
                result.receipt_id = receipt.receipt_id
                self.store.increment_usage(rule.rule_id)
                return result
            if result.decision not in (
                AutoApprovalRuleDecision.AUTO_APPROVE_DENIED,
                AutoApprovalRuleDecision.AUTO_APPROVE_SCOPE_MISMATCH,
            ):
                return result

        return AutoApprovalEvaluation(
            AutoApprovalRuleDecision.AUTO_APPROVE_DENIED,
            "no matching active rule",
        )

    def _evaluate_rule(
        self,
        rule: AutoApprovalRule,
        item: OperatorQueueItem,
        *,
        domain: str | None,
    ) -> AutoApprovalEvaluation:
        if rule.status == AutoApprovalRuleStatus.REVOKED:
            return AutoApprovalEvaluation(AutoApprovalRuleDecision.AUTO_APPROVE_REVOKED, "revoked", rule.rule_id)
        if _parse_expiry(rule.expires_at):
            rule.status = AutoApprovalRuleStatus.EXPIRED
            self.store.update_rule(rule)
            write_rule_event_receipt(self.store, rule, AutoApprovalRuleDecision.AUTO_APPROVE_EXPIRED, "expired")
            return AutoApprovalEvaluation(AutoApprovalRuleDecision.AUTO_APPROVE_EXPIRED, "rule expired", rule.rule_id)

        if rule.action_type != item.action_type:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_SCOPE_MISMATCH,
                "action_type mismatch",
                rule.rule_id,
            )

        if not risk_within_ceiling(item.action_type, rule.max_risk_class):
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_RISK_TOO_HIGH,
                "risk above ceiling",
                rule.rule_id,
            )

        surface = item.requested_surface.value
        if rule.allowed_surfaces and surface not in rule.allowed_surfaces:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_SCOPE_MISMATCH,
                "surface mismatch",
                rule.rule_id,
            )

        if rule.allowed_domains and domain and domain not in rule.allowed_domains:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_SCOPE_MISMATCH,
                "domain mismatch",
                rule.rule_id,
            )

        usage = self.store._usage.get(rule.rule_id, {})
        if usage.get("run", 0) >= rule.max_count_per_run:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_RATE_LIMITED,
                "run limit",
                rule.rule_id,
            )
        if usage.get("hour", 0) >= rule.max_count_per_hour:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_RATE_LIMITED,
                "hour limit",
                rule.rule_id,
            )
        if usage.get("day", 0) >= rule.max_count_per_day:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_RATE_LIMITED,
                "day limit",
                rule.rule_id,
            )

        tb = item.action_request.trust_boundary_verdict
        if tb and rule.required_trust_boundary_verdict:
            if not tb.upper().startswith(rule.required_trust_boundary_verdict.split("_")[0].upper()):
                return AutoApprovalEvaluation(
                    AutoApprovalRuleDecision.AUTO_APPROVE_DENIED,
                    "trust boundary mismatch",
                    rule.rule_id,
                )

        if rule.dry_run_only:
            return AutoApprovalEvaluation(
                AutoApprovalRuleDecision.AUTO_APPROVE_DRY_RUN_ONLY,
                "dry-run only rule",
                rule.rule_id,
            )

        return AutoApprovalEvaluation(
            AutoApprovalRuleDecision.AUTO_APPROVE_ALLOWED,
            "rule matched",
            rule.rule_id,
        )


__all__ = ["AutoApprovalEvaluator"]
