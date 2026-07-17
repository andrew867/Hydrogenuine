"""CapabilityMenuSnapshot — action menu for future reasoning."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.types import ALLOWED_ACTION_IDS, FORBIDDEN_ACTION_IDS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


EXTERNAL_BOUND_ACTIONS = frozenset({
    "observe_social",
})


@dataclass
class CapabilityMenuAction:
    action_id: str
    display_name: str
    internal_only: bool
    external_side_effect: bool
    requires_operator: bool
    requires_provider: bool
    requires_live_read: bool
    requires_broker: bool
    enabled: bool
    disabled_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "display_name": self.display_name,
            "internal_only": self.internal_only,
            "external_side_effect": self.external_side_effect,
            "requires_operator": self.requires_operator,
            "requires_provider": self.requires_provider,
            "requires_live_read": self.requires_live_read,
            "requires_broker": self.requires_broker,
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason,
        }


@dataclass
class CapabilityMenuSnapshot:
    menu_id: str
    runtime_mode: str
    operator_presence: str
    actions: list[CapabilityMenuAction]
    forbidden_actions: list[str]
    generated_at: str
    policy_refs: list[str]
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "menu_id": self.menu_id,
            "runtime_mode": self.runtime_mode,
            "operator_presence": self.operator_presence,
            "actions": [a.to_payload() for a in self.actions],
            "forbidden_actions": list(self.forbidden_actions),
            "generated_at": self.generated_at,
            "policy_refs": list(self.policy_refs),
            "hash": self.hash,
        }

    def with_hash(self) -> CapabilityMenuSnapshot:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return CapabilityMenuSnapshot(**{**self.__dict__, "hash": hash_record(body)})

    def allowed_action_ids(self) -> frozenset[str]:
        return frozenset(a.action_id for a in self.actions if a.enabled)


def _base_actions() -> list[CapabilityMenuAction]:
    specs = [
        ("observe_social", "Observe social (read-only)", False, False, False, False, True, True),
        ("synthesize_notes", "Synthesize internal notes", True, False, False, True, False, False),
        ("propose_draft", "Propose draft for review", True, False, False, True, False, True),
        ("propose_operator_question", "Ask operator a question", True, False, False, False, False, False),
        ("request_more_scope", "Request more scope", True, False, False, False, False, False),
        ("continue_prior_thread", "Continue prior thread internally", True, False, False, False, False, False),
        ("rest_turn", "Rest turn", True, False, False, False, False, False),
        ("witness_turn", "Witness turn", True, False, False, False, False, False),
    ]
    return [
        CapabilityMenuAction(
            action_id=aid,
            display_name=name,
            internal_only=internal,
            external_side_effect=external,
            requires_operator=req_op,
            requires_provider=req_prov,
            requires_live_read=req_read,
            requires_broker=req_broker,
            enabled=True,
        )
        for aid, name, internal, external, req_op, req_prov, req_read, req_broker in specs
    ]


def build_capability_menu(
    *,
    runtime_mode: str,
    operator_presence: str = "operator_present",
    provider_available: bool = True,
    live_read_available: bool = True,
    policy_refs: list[str] | None = None,
) -> CapabilityMenuSnapshot:
    """Build capability menu with operator/provider/read constraints."""
    actions = _base_actions()
    restrictive = operator_presence in (
        "operator_absent",
        "operator_unknown",
        "operator_stale",
    )
    updated: list[CapabilityMenuAction] = []
    for action in actions:
        enabled = action.enabled
        reason = action.disabled_reason
        if action.action_id in FORBIDDEN_ACTION_IDS:
            enabled = False
            reason = "forbidden_in_phase_5"
        if action.external_side_effect:
            enabled = False
            reason = "external_write_not_allowed_phase_5"
        if restrictive and not action.internal_only:
            enabled = False
            reason = "operator_absent"
        if action.requires_provider and not provider_available:
            enabled = False
            reason = "provider_unavailable"
        if action.requires_live_read and not live_read_available:
            enabled = False
            reason = "live_read_unavailable"
        updated.append(
            CapabilityMenuAction(
                action_id=action.action_id,
                display_name=action.display_name,
                internal_only=action.internal_only,
                external_side_effect=action.external_side_effect,
                requires_operator=action.requires_operator,
                requires_provider=action.requires_provider,
                requires_live_read=action.requires_live_read,
                requires_broker=action.requires_broker,
                enabled=enabled,
                disabled_reason=reason,
            )
        )
    menu = CapabilityMenuSnapshot(
        menu_id=f"menu-{uuid.uuid4().hex[:12]}",
        runtime_mode=runtime_mode,
        operator_presence=operator_presence,
        actions=updated,
        forbidden_actions=sorted(FORBIDDEN_ACTION_IDS),
        generated_at=_now_iso(),
        policy_refs=list(policy_refs or ["configs/agent_zero/turn_state_policy.json"]),
    ).with_hash()
    return menu


def validate_capability_menu(menu: CapabilityMenuSnapshot) -> bool:
    if not menu.hash:
        return False
    body = {k: v for k, v in menu.to_payload().items() if k != "hash"}
    if not verify_record_hash(body, menu.hash):
        return False
    for action in menu.actions:
        if action.action_id in FORBIDDEN_ACTION_IDS and action.enabled:
            return False
        if action.action_id not in ALLOWED_ACTION_IDS:
            return False
    return True


__all__ = [
    "CapabilityMenuAction",
    "CapabilityMenuSnapshot",
    "build_capability_menu",
    "validate_capability_menu",
]
