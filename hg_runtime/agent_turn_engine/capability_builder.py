"""Capability menu builder for agent turn engine."""

from __future__ import annotations

from hg_runtime.agent_zero_state.capability_menu import (
    CapabilityMenuAction,
    CapabilityMenuSnapshot,
    build_capability_menu,
)
from hg_runtime.agent_zero_state.observe_snapshot import ObserveSnapshot
from hg_runtime.agent_zero_state.state import AgentState
from hg_runtime.agent_turn_engine.schema import PHASE_9_IMPLEMENTED_ACTIONS

DISABLED_REASON_NO_PROVIDER = "YELLOW_PROVIDER_UNAVAILABLE_DRAFT_ACTIONS_DEFERRED"
DISABLED_REASON_NO_HANDLER = "handler_not_implemented"


def build_capability_menu_for_turn(
    *,
    agent_state: AgentState,
    observe_snapshot: ObserveSnapshot,
    operator_presence: str,
    provider_status: str,
    live_read_status: str,
) -> CapabilityMenuSnapshot:
    """Build menu with Phase 9 implemented handlers."""
    provider_available = provider_status == "available" or bool(observe_snapshot.provider_reality_refs)
    live_read_available = live_read_status == "available" or bool(observe_snapshot.live_read_receipt_refs)

    base = build_capability_menu(
        runtime_mode=agent_state.runtime_mode,
        operator_presence=operator_presence,
        provider_available=provider_available,
        live_read_available=live_read_available,
        policy_refs=[
            "configs/agent_zero/agent_turn_engine_policy.json",
            "configs/agent_zero/output_quality_policy.json",
        ],
    )

    updated: list[CapabilityMenuAction] = []
    for action in base.actions:
        enabled = action.enabled
        reason = action.disabled_reason
        if action.action_id not in PHASE_9_IMPLEMENTED_ACTIONS:
            enabled = False
            reason = DISABLED_REASON_NO_HANDLER
        elif action.action_id in ("synthesize_notes", "propose_draft", "continue_prior_thread") and not provider_available:
            enabled = False
            reason = DISABLED_REASON_NO_PROVIDER
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
        menu_id=base.menu_id,
        runtime_mode=base.runtime_mode,
        operator_presence=base.operator_presence,
        actions=updated,
        forbidden_actions=list(base.forbidden_actions),
        generated_at=base.generated_at,
        policy_refs=list(base.policy_refs),
        hash="",
    ).with_hash()
    return menu


__all__ = ["DISABLED_REASON_NO_PROVIDER", "build_capability_menu_for_turn"]
