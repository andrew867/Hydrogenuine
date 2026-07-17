"""Receipt construction helpers for the EXCITON action model."""

from __future__ import annotations

from hg_runtime.exciton_action_model.schema import (
    AgentActionDecision,
    AgentActionDecisionKind,
    AgentActionReceipt,
    AgentActionRequest,
    FIXTURE_UTC,
    new_receipt_id,
)


def receipt_from_decision(
    decision: AgentActionDecision,
    *,
    previous_receipt_ref: str | None = None,
) -> AgentActionReceipt:
    return AgentActionReceipt(
        receipt_id=new_receipt_id(),
        action_id=decision.action_id,
        action_type=decision.action_type,
        decision=decision.decision,
        reason=decision.reason,
        operator_ref=decision.operator_ref,
        policy_refs=list(decision.policy_refs),
        proof_refs=list(decision.proof_refs),
        created_at=decision.created_at,
        previous_receipt_ref=previous_receipt_ref,
    )


def enqueue_receipt(request: AgentActionRequest) -> AgentActionReceipt:
    return AgentActionReceipt(
        receipt_id=new_receipt_id(),
        action_id=request.action_id,
        action_type=request.action_type,
        decision=AgentActionDecisionKind.QUEUE_FOR_OPERATOR,
        reason="action enqueued for operator review",
        created_at=request.created_at or FIXTURE_UTC,
        policy_refs=list(request.policy_refs),
        proof_refs=list(request.proof_refs),
    )


__all__ = ["enqueue_receipt", "receipt_from_decision"]
