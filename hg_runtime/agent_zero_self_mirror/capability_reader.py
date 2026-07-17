"""Capability reflection for self mirror."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.schema import CapabilityIndex, IndexStatus
from hg_runtime.tool_capability_fabric.registry import load_registry


def build_capability_index() -> CapabilityIndex:
    reg = load_registry()
    caps = []
    for cap in sorted(reg.capabilities.values(), key=lambda c: c.capability_id):
        status = "enabled" if cap.enabled else "disabled"
        if cap.risk_class in {"high", "critical"}:
            approval = "full_stop_or_review"
        elif cap.requires_operator_approval:
            approval = "review"
        else:
            approval = "denied_by_default" if not cap.enabled else "requestable"
        caps.append({
            "capability_id": cap.capability_id,
            "name": cap.name,
            "class": cap.capability_class,
            "enabled": cap.enabled,
            "live_enabled": cap.live_enabled,
            "approval_class": approval,
            "read_only": cap.read_only,
            "draft_only": cap.draft_only,
            "risk_class": cap.risk_class,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        })
    return CapabilityIndex(status=IndexStatus.READY, capabilities=caps)


def list_forbidden_capabilities() -> list[str]:
    idx = build_capability_index()
    return [c["capability_id"] for c in idx.capabilities if not c["enabled"] or c["approval_class"] == "full_stop_or_review"]


def list_requestable_capabilities() -> list[str]:
    idx = build_capability_index()
    return [c["capability_id"] for c in idx.capabilities if c["enabled"] and c["approval_class"] != "full_stop_or_review"]


__all__ = ["build_capability_index", "list_forbidden_capabilities", "list_requestable_capabilities"]
