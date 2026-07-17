"""UEAK Phase 1 effect-class policy stubs."""

from __future__ import annotations

PERMIT_REQUIRED_EFFECT_CLASSES = frozenset({"external_write"})

ACTION_CAPABILITY_DEFAULTS = {
    "oea_stub_log": ("cap.oea_stub_log", "audit_log"),
    "memory_write_stub": ("cap.memory_write_stub", "derived_store"),
    "external_post": ("cap.external_post", "external_write"),
    "external_write_scaffold": ("cap.external_write_scaffold", "external_write"),
    "local_report_file_write": ("local_report_file.write", "local_report"),
}


def effect_requires_permit(effect_class: str) -> bool:
    return effect_class in PERMIT_REQUIRED_EFFECT_CLASSES


def resolve_capability_for_action(action: dict) -> tuple[str, str]:
    capability_id = str(action.get("capability_id") or "")
    effect_class = str(action.get("effect_class") or "")
    if capability_id and effect_class:
        return capability_id, effect_class
    action_type = str(action.get("action_type") or "")
    defaults = ACTION_CAPABILITY_DEFAULTS.get(action_type)
    if defaults is None:
        return capability_id or "cap.unknown", effect_class or "unknown"
    return defaults


__all__ = [
    "ACTION_CAPABILITY_DEFAULTS",
    "PERMIT_REQUIRED_EFFECT_CLASSES",
    "effect_requires_permit",
    "resolve_capability_for_action",
]
