"""TurnIntent — candidate action shape for future reasoning."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hg_runtime.agent_zero_state.capability_menu import CapabilityMenuSnapshot
from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.redaction import scan_payload
from hg_runtime.agent_zero_state.types import TurnIntentVerdict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TurnIntent:
    intent_id: str
    agent_id: str
    turn_index: int
    chosen_action: str
    action_params: dict[str, Any]
    observation_summary: str
    why_this_action: str
    alternatives_considered: list[str]
    why_not_others: str
    uncertainty: str
    operator_questions: list[str]
    scope_requests: list[str]
    created_at: str
    hash: str = ""
    run_id: str | None = None
    witness_mode_requested: str | None = None
    prompt_hash: str | None = None
    provider_receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "chosen_action": self.chosen_action,
            "action_params": dict(self.action_params),
            "observation_summary": self.observation_summary,
            "why_this_action": self.why_this_action,
            "alternatives_considered": list(self.alternatives_considered),
            "why_not_others": self.why_not_others,
            "uncertainty": self.uncertainty,
            "operator_questions": list(self.operator_questions),
            "scope_requests": list(self.scope_requests),
            "witness_mode_requested": self.witness_mode_requested,
            "created_at": self.created_at,
            "prompt_hash": self.prompt_hash,
            "provider_receipt_ref": self.provider_receipt_ref,
            "hash": self.hash,
        }

    def with_hash(self) -> TurnIntent:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return TurnIntent(**{**self.__dict__, "hash": hash_record(body)})


def build_turn_intent(
    *,
    agent_id: str,
    turn_index: int,
    chosen_action: str,
    menu: CapabilityMenuSnapshot,
    observation_summary: str = "",
    why_this_action: str = "",
    action_params: dict[str, Any] | None = None,
    alternatives_considered: list[str] | None = None,
    why_not_others: str = "",
    uncertainty: str = "",
    operator_questions: list[str] | None = None,
    scope_requests: list[str] | None = None,
    witness_mode_requested: str | None = None,
    run_id: str | None = None,
    provider_receipt_ref: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> tuple[TurnIntentVerdict, TurnIntent]:
    """Build and validate turn intent against capability menu."""
    if extra_fields:
        has_secret, has_cot = scan_payload(extra_fields)
        if has_secret:
            return TurnIntentVerdict.RED_TURN_INTENT_SECRET_LEAK, TurnIntent(
                intent_id="invalid",
                agent_id=agent_id,
                turn_index=turn_index,
                chosen_action=chosen_action,
                action_params={},
                observation_summary="",
                why_this_action="",
                alternatives_considered=[],
                why_not_others="",
                uncertainty="",
                operator_questions=[],
                scope_requests=[],
                created_at=_now_iso(),
            )
        if has_cot:
            return TurnIntentVerdict.RED_TURN_INTENT_COT_LEAK, TurnIntent(
                intent_id="invalid",
                agent_id=agent_id,
                turn_index=turn_index,
                chosen_action=chosen_action,
                action_params={},
                observation_summary="",
                why_this_action="",
                alternatives_considered=[],
                why_not_others="",
                uncertainty="",
                operator_questions=[],
                scope_requests=[],
                created_at=_now_iso(),
            )

    if not chosen_action or not agent_id:
        return TurnIntentVerdict.RED_TURN_INTENT_EMPTY, TurnIntent(
            intent_id="empty",
            agent_id=agent_id or "",
            turn_index=turn_index,
            chosen_action=chosen_action or "",
            action_params={},
            observation_summary=observation_summary,
            why_this_action=why_this_action,
            alternatives_considered=list(alternatives_considered or []),
            why_not_others=why_not_others,
            uncertainty=uncertainty,
            operator_questions=list(operator_questions or []),
            scope_requests=list(scope_requests or []),
            created_at=_now_iso(),
        )

    if chosen_action not in menu.allowed_action_ids():
        return TurnIntentVerdict.RED_TURN_INTENT_UNKNOWN_ACTION, TurnIntent(
            intent_id=f"intent-{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            turn_index=turn_index,
            chosen_action=chosen_action,
            action_params=dict(action_params or {}),
            observation_summary=observation_summary,
            why_this_action=why_this_action,
            alternatives_considered=list(alternatives_considered or []),
            why_not_others=why_not_others,
            uncertainty=uncertainty,
            operator_questions=list(operator_questions or []),
            scope_requests=list(scope_requests or []),
            created_at=_now_iso(),
        )

    intent = TurnIntent(
        intent_id=f"intent-{uuid.uuid4().hex[:12]}",
        agent_id=agent_id,
        run_id=run_id,
        turn_index=turn_index,
        chosen_action=chosen_action,
        action_params=dict(action_params or {}),
        observation_summary=observation_summary.strip(),
        why_this_action=why_this_action.strip(),
        alternatives_considered=list(alternatives_considered or []),
        why_not_others=why_not_others.strip(),
        uncertainty=uncertainty.strip(),
        operator_questions=list(operator_questions or []),
        scope_requests=list(scope_requests or []),
        witness_mode_requested=witness_mode_requested,
        provider_receipt_ref=provider_receipt_ref,
        created_at=_now_iso(),
    ).with_hash()
    return validate_turn_intent(intent)


def validate_turn_intent(intent: TurnIntent) -> tuple[TurnIntentVerdict, TurnIntent]:
    payload = intent.to_payload()
    has_secret, has_cot = scan_payload(payload)
    if has_secret:
        return TurnIntentVerdict.RED_TURN_INTENT_SECRET_LEAK, intent
    if has_cot:
        return TurnIntentVerdict.RED_TURN_INTENT_COT_LEAK, intent
    if not intent.chosen_action or not intent.agent_id:
        return TurnIntentVerdict.RED_TURN_INTENT_EMPTY, intent
    if not intent.hash or not verify_record_hash(
        {k: v for k, v in payload.items() if k != "hash"}, intent.hash
    ):
        return TurnIntentVerdict.RED_TURN_INTENT_EMPTY, intent
    return TurnIntentVerdict.GREEN_TURN_INTENT_VALID, intent


__all__ = ["TurnIntent", "build_turn_intent", "validate_turn_intent"]
