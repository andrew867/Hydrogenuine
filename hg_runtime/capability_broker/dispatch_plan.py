"""Dispatch plan — advisory only, no execution in Phase 7."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.capability_broker.action_registry import get_action


class DispatchVerdict(str, Enum):
    GREEN_INTERNAL_DISPATCH_PLAN_CREATED = "GREEN_INTERNAL_DISPATCH_PLAN_CREATED"
    RED_DISPATCH_EXECUTION_ATTEMPTED = "RED_DISPATCH_EXECUTION_ATTEMPTED"
    RED_DISPATCH_EXTERNAL_SIDE_EFFECT = "RED_DISPATCH_EXTERNAL_SIDE_EFFECT"


@dataclass
class DispatchPlan:
    dispatch_plan_id: str
    decision_id: str
    action_id: str
    internal_only: bool
    execution_allowed: bool
    external_side_effect: bool
    required_receipts: list[str]
    created_at: str
    hash: str = ""
    target_module: str | None = None
    verdict: DispatchVerdict = DispatchVerdict.GREEN_INTERNAL_DISPATCH_PLAN_CREATED

    def to_payload(self) -> dict[str, Any]:
        return {
            "dispatch_plan_id": self.dispatch_plan_id,
            "decision_id": self.decision_id,
            "action_id": self.action_id,
            "internal_only": self.internal_only,
            "execution_allowed": self.execution_allowed,
            "external_side_effect": self.external_side_effect,
            "target_module": self.target_module,
            "required_receipts": list(self.required_receipts),
            "verdict": self.verdict.value,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> DispatchPlan:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DispatchPlan(**{**self.__dict__, "hash": hash_record(body)})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_dispatch_plan(
    *,
    decision_id: str,
    action_id: str,
    required_receipts: list[str] | None = None,
) -> DispatchPlan:
    """Create internal-only dispatch plan — execution_allowed always false."""
    action = get_action(action_id)
    if action and action.external_side_effect:
        plan = DispatchPlan(
            dispatch_plan_id=f"dispatch-{uuid.uuid4().hex[:12]}",
            decision_id=decision_id,
            action_id=action_id,
            internal_only=False,
            execution_allowed=False,
            external_side_effect=True,
            required_receipts=list(required_receipts or []),
            created_at=_now_iso(),
            verdict=DispatchVerdict.RED_DISPATCH_EXTERNAL_SIDE_EFFECT,
        ).with_hash()
        return plan

    plan = DispatchPlan(
        dispatch_plan_id=f"dispatch-{uuid.uuid4().hex[:12]}",
        decision_id=decision_id,
        action_id=action_id,
        internal_only=True,
        execution_allowed=False,
        external_side_effect=False,
        required_receipts=list(required_receipts or []),
        created_at=_now_iso(),
        target_module="future_agent_turn_engine",
        verdict=DispatchVerdict.GREEN_INTERNAL_DISPATCH_PLAN_CREATED,
    ).with_hash()
    return validate_dispatch_plan(plan)


def validate_dispatch_plan(plan: DispatchPlan) -> DispatchPlan:
    if plan.execution_allowed:
        raise ValueError(DispatchVerdict.RED_DISPATCH_EXECUTION_ATTEMPTED.value)
    if plan.external_side_effect:
        return DispatchPlan(**{**plan.__dict__, "verdict": DispatchVerdict.RED_DISPATCH_EXTERNAL_SIDE_EFFECT})
    body = {k: v for k, v in plan.to_payload().items() if k != "hash"}
    if not plan.hash or not verify_record_hash(body, plan.hash):
        raise ValueError("dispatch plan hash invalid")
    return plan


__all__ = [
    "DispatchPlan",
    "DispatchVerdict",
    "create_dispatch_plan",
    "validate_dispatch_plan",
]
