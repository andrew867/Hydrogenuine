"""Action registry for capability broker."""

from __future__ import annotations

from hg_runtime.agent_zero_state.hashing import hash_record
from hg_runtime.agent_zero_state.types import ALLOWED_ACTION_IDS, FORBIDDEN_ACTION_IDS
from hg_runtime.capability_broker.schema import CapabilityAction

PHASE_ALLOWED = 7

REGISTRY: dict[str, CapabilityAction] = {
    "observe_social": CapabilityAction(
        action_id="observe_social",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=False,
        requires_live_read=True,
        requires_output_quality=False,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=PHASE_ALLOWED,
        description="Read-only social observation",
    ),
    "synthesize_notes": CapabilityAction(
        action_id="synthesize_notes",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=False,
        requires_live_read=False,
        requires_output_quality=False,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=PHASE_ALLOWED,
        description="Synthesize internal notes",
    ),
    "propose_draft": CapabilityAction(
        action_id="propose_draft",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=True,
        requires_live_read=False,
        requires_output_quality=True,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=PHASE_ALLOWED,
        description="Propose draft for operator review",
    ),
    "propose_operator_question": CapabilityAction(
        action_id="propose_operator_question",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=False,
        requires_live_read=False,
        requires_output_quality=False,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=PHASE_ALLOWED,
        description="Ask operator a question",
    ),
    "request_more_scope": CapabilityAction(
        action_id="request_more_scope",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=False,
        requires_live_read=False,
        requires_output_quality=False,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=PHASE_ALLOWED,
        description="Request expanded scope",
    ),
    "continue_prior_thread": CapabilityAction(
        action_id="continue_prior_thread",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=False,
        requires_live_read=False,
        requires_output_quality=False,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=PHASE_ALLOWED,
        description="Continue prior thread internally",
    ),
    "rest_turn": CapabilityAction(
        action_id="rest_turn",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=False,
        requires_live_read=False,
        requires_output_quality=False,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=PHASE_ALLOWED,
        description="Rest turn",
    ),
    "witness_turn": CapabilityAction(
        action_id="witness_turn",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=False,
        requires_live_read=False,
        requires_output_quality=False,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=PHASE_ALLOWED,
        description="Witness turn",
    ),
    "create_external_action_candidate": CapabilityAction(
        action_id="create_external_action_candidate",
        internal_only=True,
        external_side_effect=False,
        requires_operator=False,
        requires_provider=False,
        requires_live_read=False,
        requires_output_quality=False,
        requires_broker=True,
        enabled_by_default=True,
        phase_allowed=17,
        description="Create external write candidate — not permission, not dispatch",
    ),
}

FORBIDDEN_REGISTRY_ACTIONS = frozenset({
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
    "shell_exec",
    "filesystem_mutate_unbounded",
    "network_write",
})


def get_action(action_id: str) -> CapabilityAction | None:
    return REGISTRY.get(action_id)


def is_forbidden_action(action_id: str) -> bool:
    return action_id in FORBIDDEN_ACTION_IDS or action_id in FORBIDDEN_REGISTRY_ACTIONS


def is_known_action(action_id: str) -> bool:
    return action_id in REGISTRY and action_id in ALLOWED_ACTION_IDS


def registry_hash() -> str:
    payload = {aid: action.to_payload() for aid, action in sorted(REGISTRY.items())}
    return hash_record(payload)


def all_registered_actions() -> list[CapabilityAction]:
    return list(REGISTRY.values())


__all__ = [
    "FORBIDDEN_REGISTRY_ACTIONS",
    "REGISTRY",
    "all_registered_actions",
    "get_action",
    "is_forbidden_action",
    "is_known_action",
    "registry_hash",
]
