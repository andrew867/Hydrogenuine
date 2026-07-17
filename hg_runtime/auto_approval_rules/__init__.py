"""Scoped auto-approval rules — policy, not authority."""

from hg_runtime.auto_approval_rules.adapters import create_readonly_fixture_rule, evaluate_queue_item
from hg_runtime.auto_approval_rules.errors import (
    AutoApprovalError,
    ForbiddenRuleTypeError,
    RateLimitExceededError,
    RuleNotFoundError,
    RuleValidationError,
)
from hg_runtime.auto_approval_rules.evaluator import AutoApprovalEvaluator
from hg_runtime.auto_approval_rules.policy import (
    ALLOWED_RULE_ACTION_TYPES,
    FORBIDDEN_RULE_ACTION_TYPES,
    is_forbidden_rule_action_type,
    risk_within_ceiling,
    validate_rule_scope,
)
from hg_runtime.auto_approval_rules.revocation import revoke_rule
from hg_runtime.auto_approval_rules.schema import (
    AGENT0_ID,
    AutoApprovalEvaluation,
    AutoApprovalRevocation,
    AutoApprovalRule,
    AutoApprovalRuleDecision,
    AutoApprovalRuleReceipt,
    AutoApprovalRuleScope,
    AutoApprovalRuleStatus,
    new_receipt_id,
    new_rule_id,
)
from hg_runtime.auto_approval_rules.store import AutoApprovalRuleStore

__all__ = [
    "AGENT0_ID",
    "ALLOWED_RULE_ACTION_TYPES",
    "AutoApprovalError",
    "AutoApprovalEvaluation",
    "AutoApprovalEvaluator",
    "AutoApprovalRevocation",
    "AutoApprovalRule",
    "AutoApprovalRuleDecision",
    "AutoApprovalRuleReceipt",
    "AutoApprovalRuleScope",
    "AutoApprovalRuleStatus",
    "AutoApprovalRuleStore",
    "FORBIDDEN_RULE_ACTION_TYPES",
    "ForbiddenRuleTypeError",
    "RateLimitExceededError",
    "RuleNotFoundError",
    "RuleValidationError",
    "create_readonly_fixture_rule",
    "evaluate_queue_item",
    "is_forbidden_rule_action_type",
    "new_receipt_id",
    "new_rule_id",
    "revoke_rule",
    "risk_within_ceiling",
    "validate_rule_scope",
]
