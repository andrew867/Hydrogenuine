"""RTC draft emission for boundary organs — loop-owned bus, no direct authority."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from hg_runtime.contract import draft


def feature_enabled(env_name: str, *, default: str = "0") -> bool:
    import os

    return os.environ.get(env_name, default).strip() == "1"


def boundary_draft(
    event_type: str,
    payload: dict[str, Any],
    *,
    causal_parents: Sequence[str] = (),
) -> dict[str, Any]:
    body = {**payload, "observation_only": True, "permission_granted": False, "authority_created": False}
    return draft(event_type, body, causal_parents=causal_parents)


def emit_drafts(bus: Any, drafts: Sequence[dict[str, Any]], *, source: str) -> list[Mapping[str, Any]]:
    """Emit drafts when bus is available; return emitted events (or draft payloads if bus absent)."""
    emitted: list[Mapping[str, Any]] = []
    for item in drafts:
        if bus is None:
            emitted.append(item)
            continue
        if hasattr(bus, "emit_draft"):
            emitted.append(bus.emit_draft(item, source=source))
        else:
            emitted.append(item)
    return emitted


__all__ = ["boundary_draft", "emit_drafts", "feature_enabled"]
