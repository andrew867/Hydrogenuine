"""Auto-approval rule errors."""

from __future__ import annotations


class AutoApprovalError(Exception):
    pass


class RuleValidationError(AutoApprovalError):
    pass


class ForbiddenRuleTypeError(AutoApprovalError):
    pass


class RuleNotFoundError(AutoApprovalError):
    pass


class RateLimitExceededError(AutoApprovalError):
    pass


__all__ = [
    "AutoApprovalError",
    "ForbiddenRuleTypeError",
    "RateLimitExceededError",
    "RuleNotFoundError",
    "RuleValidationError",
]
