"""
OS Phase 1: Two-phase commit for high-impact side effects.
Events: ACTION_PROPOSED, ACTION_APPROVAL_REQUESTED, ACTION_APPROVAL_GRANTED/DENIED, ACTION_EXECUTED (receipt), ACTION_VERIFIED, ACTION_COMMITTED.
"""

from .two_phase import (
    propose_action,
    grant_approval,
    deny_approval,
    execute_action,
    verify_action,
    commit_action,
)

__all__ = [
    "propose_action",
    "grant_approval",
    "deny_approval",
    "execute_action",
    "verify_action",
    "commit_action",
]
