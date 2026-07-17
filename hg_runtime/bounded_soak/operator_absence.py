"""Operator absence policy — absence never expands authority."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.bounded_soak.witness_integrity import (
    WitnessIntegrityReceipt,
    WitnessMode,
    build_witness_receipt,
    enter_witness_mode,
)

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = WORKSPACE / "configs/agent_zero/operator_absence_policy.json"


class OperatorPresenceState(str, Enum):
    OPERATOR_PRESENT = "operator_present"
    OPERATOR_ABSENT = "operator_absent"
    OPERATOR_UNKNOWN = "operator_unknown"
    OPERATOR_STALE = "operator_stale"


ALLOWED_INTERNAL_ACTIONS = frozenset({
    "observe_read_only",
    "synthesize_internal_notes",
    "prepare_draft_for_review",
    "propose_operator_question",
    "request_more_scope",
    "continue_prior_thread_internal",
    "rest_turn",
    "witness_turn",
})

FORBIDDEN_EXTERNAL_ACTIONS = frozenset({
    "publish",
    "send",
    "reply_live",
    "comment_live",
    "approve",
    "approve_all",
    "browser_submit",
    "login",
    "purchase",
    "external_execute",
    "hardware_actuate",
    "scope_expand",
})


@dataclass(frozen=True)
class OperatorAbsencePolicy:
    policy_id: str
    version: str
    allowed_internal_actions: frozenset[str]
    forbidden_external_actions: frozenset[str]
    unknown_as_restrictive_as_absent: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorAbsencePolicy:
        return cls(
            policy_id=data.get("policy_id", "operator_absence_policy"),
            version=data.get("version", "1"),
            allowed_internal_actions=frozenset(data.get("allowed_internal_actions", ALLOWED_INTERNAL_ACTIONS)),
            forbidden_external_actions=frozenset(data.get("forbidden_external_actions", FORBIDDEN_EXTERNAL_ACTIONS)),
            unknown_as_restrictive_as_absent=bool(data.get("unknown_as_restrictive_as_absent", True)),
        )


@dataclass(frozen=True)
class OperatorAbsenceDecision:
    operator_state: OperatorPresenceState
    chosen_action: str
    allowed: bool
    reason: str
    refusal_verdict: str
    witness_receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "operator_state": self.operator_state.value,
            "chosen_action": self.chosen_action,
            "allowed": self.allowed,
            "reason": self.reason,
            "refusal_verdict": self.refusal_verdict,
            "witness_receipt_ref": self.witness_receipt_ref,
        }


def load_operator_absence_policy(*, path: Path | None = None) -> OperatorAbsencePolicy:
    policy_path = path or DEFAULT_POLICY_PATH
    if not policy_path.is_file():
        return OperatorAbsencePolicy(
            policy_id="operator_absence_policy",
            version="1",
            allowed_internal_actions=ALLOWED_INTERNAL_ACTIONS,
            forbidden_external_actions=FORBIDDEN_EXTERNAL_ACTIONS,
        )
    return OperatorAbsencePolicy.from_dict(json.loads(policy_path.read_text(encoding="utf-8")))


def _is_restrictive_state(state: OperatorPresenceState, policy: OperatorAbsencePolicy) -> bool:
    if state == OperatorPresenceState.OPERATOR_PRESENT:
        return False
    if state == OperatorPresenceState.OPERATOR_UNKNOWN and policy.unknown_as_restrictive_as_absent:
        return True
    return state in (
        OperatorPresenceState.OPERATOR_ABSENT,
        OperatorPresenceState.OPERATOR_UNKNOWN,
        OperatorPresenceState.OPERATOR_STALE,
    )


def evaluate_operator_absence(
    *,
    operator_state: OperatorPresenceState,
    chosen_action: str,
    policy: OperatorAbsencePolicy | None = None,
) -> OperatorAbsenceDecision:
    """Evaluate whether action is allowed given operator presence."""
    policy = policy or load_operator_absence_policy()
    action = chosen_action.strip().lower()

    if not _is_restrictive_state(operator_state, policy):
        return OperatorAbsenceDecision(
            operator_state=operator_state,
            chosen_action=action,
            allowed=True,
            reason="operator_present",
            refusal_verdict="GREEN_OPERATOR_PRESENT",
        )

    if action in policy.forbidden_external_actions:
        _, witness = enter_witness_mode(
            mode=WitnessMode.OPERATOR_ABSENT,
            reason=f"operator {operator_state.value}; external action {action} refused",
            operator_present=False,
        )
        return OperatorAbsenceDecision(
            operator_state=operator_state,
            chosen_action=action,
            allowed=False,
            reason="operator absent cannot authorize external-bound action",
            refusal_verdict="RED_OPERATOR_ABSENT_EXTERNAL_REFUSED",
            witness_receipt_ref=witness.receipt_id,
        )

    if action in policy.allowed_internal_actions:
        return OperatorAbsenceDecision(
            operator_state=operator_state,
            chosen_action=action,
            allowed=True,
            reason="internal-only action permitted under operator absence",
            refusal_verdict="YELLOW_OPERATOR_ABSENT_INTERNAL_ONLY",
        )

    return OperatorAbsenceDecision(
        operator_state=operator_state,
        chosen_action=action,
        allowed=False,
        reason="action not in allowed internal set while operator absent",
        refusal_verdict="RED_OPERATOR_ABSENT_ACTION_UNKNOWN",
    )


__all__ = [
    "ALLOWED_INTERNAL_ACTIONS",
    "FORBIDDEN_EXTERNAL_ACTIONS",
    "OperatorAbsenceDecision",
    "OperatorAbsencePolicy",
    "OperatorPresenceState",
    "evaluate_operator_absence",
    "load_operator_absence_policy",
]
