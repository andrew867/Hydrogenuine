"""EXCITON Agent Zero Console panel collectors."""

from __future__ import annotations

from hg_runtime.agent_zero_console.status_synthesis import synthesize_status
from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.message_center.store import MessageCenterStore


def _collect_console(ctx: CollectorContext):
    if ctx.offline_fixture:
        fields = {
            "data_tier": "FIXTURE",
            "chat_enabled": True,
            "status_synthesis": "Operationally stable (fixture).",
            "context_grant_count": 0,
            "proposed_action_count": 0,
            "receipt_count": 0,
            "chat_can_execute": False,
            "chat_can_send": False,
            "authority_created": False,
            "permission_granted": False,
        }
        return _panel("AgentZeroConsolePanel", ExcitonPanelState.GREEN, fields)
    try:
        status = synthesize_status(conversation_id="exciton-panel")
        fields = {
            "data_tier": "LIVE",
            "chat_enabled": True,
            "status_synthesis": status.get("synthesis", "")[:500],
            "stale_source_count": status.get("stale_count", 0),
            "missing_source_count": status.get("missing_count", 0),
            "chat_can_execute": False,
            "chat_can_send": False,
            "authority_created": False,
            "permission_granted": False,
        }
        state = ExcitonPanelState.YELLOW if status.get("red_count") else ExcitonPanelState.GREEN
        if status.get("stale_count"):
            state = ExcitonPanelState.YELLOW
        return _panel("AgentZeroConsolePanel", state, fields)
    except Exception as exc:
        return _panel(
            "AgentZeroConsolePanel",
            ExcitonPanelState.DEGRADED,
            {"chat_enabled": False, "error": str(exc)[:200]},
            degraded_reason=str(exc),
        )


def _collect_message_center(ctx: CollectorContext):
    items = MessageCenterStore().list_items()
    fields = {
        "data_tier": "FIXTURE" if ctx.offline_fixture else "LIVE",
        "message_count": len(items),
        "live_import_disabled": True,
        "live_send_disabled": True,
        "cargo_boundary": True,
        "authority_created": False,
        "permission_granted": False,
    }
    return _panel("MessageCenterPanel", ExcitonPanelState.GREEN, fields)


def build_agent_zero_console_panels(ctx: CollectorContext) -> list:
    return [_collect_console(ctx), _collect_message_center(ctx)]


__all__ = ["build_agent_zero_console_panels"]
