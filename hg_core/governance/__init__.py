"""
OS Phase 4–Post Phase 5: Governance contracts and UX.

Contracts:
- GOVERNANCE_CONTRACT_PUBLISHED, APPROVAL_POLICY_APPLIED,
  DELEGATION_CONTRACT_CREATED, ESCALATION_ROUTE_TAKEN.

UX (Post Phase 5):
- APPROVAL_BATCH_CREATED / APPROVED
- APPROVAL_FATIGUE_LIMIT_REACHED
- AUDIT_SPOTCHECK_REQUESTED / COMPLETED
"""

from .contracts import (
    publish_governance_contract,
    record_approval_policy_applied,
    create_delegation_contract,
    record_escalation_route_taken,
    load_contract,
)
from .ux.batching import (
    rank_approvals_by_risk,
    rank_approval_queue_with_gap,
    create_approval_batch,
    record_approval_batch_approved,
    record_fatigue_limit_reached,
    request_audit_spotcheck,
    record_audit_spotcheck_completed,
)
from .independence import (
    check_closed_loop,
    require_independent_review,
    assign_reviewer,
    reject_approval_independence,
    assign_spotcheck,
)
from .trace_emitter import TraceEmitter, validate_chain as validate_trace_chain

__all__ = [
    "publish_governance_contract",
    "record_approval_policy_applied",
    "create_delegation_contract",
    "record_escalation_route_taken",
    "load_contract",
    "rank_approvals_by_risk",
    "rank_approval_queue_with_gap",
    "create_approval_batch",
    "record_approval_batch_approved",
    "record_fatigue_limit_reached",
    "request_audit_spotcheck",
    "record_audit_spotcheck_completed",
    "check_closed_loop",
    "require_independent_review",
    "assign_reviewer",
    "reject_approval_independence",
    "assign_spotcheck",
    "TraceEmitter",
    "validate_trace_chain",
]
