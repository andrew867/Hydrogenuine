"""Capability registry loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.tool_capability_fabric.types import CapabilityDefinition, advisory_envelope, stable_hash

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = WORKSPACE / "configs" / "tools" / "tool_capability_registry.example.json"


class CapabilityRegistry:
    def __init__(self, capabilities: dict[str, CapabilityDefinition]) -> None:
        self.capabilities = capabilities

    def get(self, capability_id: str) -> CapabilityDefinition | None:
        return self.capabilities.get(capability_id)

    def list_enabled(self) -> list[CapabilityDefinition]:
        return [c for c in self.capabilities.values() if c.enabled]

    def build_manifest(self, *, organ_id: str | None = None, role: str | None = None) -> dict[str, Any]:
        items = []
        for cap in sorted(self.capabilities.values(), key=lambda c: c.capability_id):
            if organ_id and cap.allowed_organs and organ_id not in cap.allowed_organs:
                continue
            if role and cap.allowed_roles and role not in cap.allowed_roles:
                continue
            items.append(cap.to_payload())
        payload = advisory_envelope(
            schema="capability-manifest",
            capability_count=len(items),
            capabilities=items,
            organ_id=organ_id,
            role=role,
            live_connectors_disabled=not any(c.live_enabled for c in self.capabilities.values()),
        )
        payload["manifest_hash"] = stable_hash({"capabilities": items})
        return payload


def _parse_capability(raw: dict[str, Any]) -> CapabilityDefinition:
    if raw.get("permission_granted") or raw.get("authority_created"):
        raise ValueError(f"capability {raw.get('capability_id')} cannot grant authority")
    return CapabilityDefinition(
        capability_id=raw["capability_id"],
        name=raw["name"],
        capability_class=raw["class"],
        provider=raw.get("provider", "local"),
        enabled=bool(raw.get("enabled", False)),
        live_enabled=bool(raw.get("live_enabled", False)),
        draft_only=bool(raw.get("draft_only", False)),
        read_only=bool(raw.get("read_only", False)),
        requires_operator_approval=bool(raw.get("requires_operator_approval", False)),
        requires_gpp_permit=bool(raw.get("requires_gpp_permit", False)),
        requires_ueak_admission=bool(raw.get("requires_ueak_admission", False)),
        requires_oauth_secret=bool(raw.get("requires_oauth_secret", False)),
        external_network_required=bool(raw.get("external_network_required", False)),
        data_policy=raw.get("data_policy", "advisory"),
        retention_policy=raw.get("retention_policy", "session"),
        risk_class=raw.get("risk_class", "low"),
        allowed_roles=list(raw.get("allowed_roles", [])),
        allowed_organs=list(raw.get("allowed_organs", [])),
        default_timeout_seconds=int(raw.get("default_timeout_seconds", 30)),
        max_rate=int(raw.get("max_rate", 60)),
    )


def load_registry(path: Path | str | None = None) -> CapabilityRegistry:
    p = Path(path) if path else DEFAULT_REGISTRY
    if not p.is_file():
        p = WORKSPACE / p
    data = json.loads(p.read_text(encoding="utf-8"))
    caps = {_parse_capability(item).capability_id: _parse_capability(item) for item in data.get("capabilities", [])}
    return CapabilityRegistry(caps)


__all__ = ["CapabilityRegistry", "DEFAULT_REGISTRY", "load_registry"]
