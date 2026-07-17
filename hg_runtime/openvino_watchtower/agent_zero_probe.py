"""Agent Zero organ activity probe — semantic layer over known organs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hg_runtime.openvino_watchtower.schema import OrganActivityEvent, OrganState

KNOWN_ORGANS: tuple[str, ...] = (
    "CHRONO",
    "WILL",
    "EXCITON",
    "social_lane",
    "web_queue",
    "operator_queue",
    "model_provider",
    "audio",
    "storage",
    "observer",
    "soak_supervisor",
)


def default_organ_map() -> dict[str, OrganActivityEvent]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        organ: OrganActivityEvent(organ_id=organ, state="idle", updated_at=now)
        for organ in KNOWN_ORGANS
    }


def merge_organ_events(existing: dict[str, OrganActivityEvent], updates: dict[str, Any]) -> dict[str, OrganActivityEvent]:
    merged = dict(existing)
    for organ_id, payload in updates.items():
        if isinstance(payload, OrganActivityEvent):
            merged[organ_id] = payload
            continue
        if not isinstance(payload, dict):
            continue
        prev = merged.get(organ_id) or OrganActivityEvent(organ_id=organ_id)
        merged[organ_id] = OrganActivityEvent(
            organ_id=organ_id,
            state=payload.get("state", prev.state),
            task=payload.get("task", prev.task),
            updated_at=payload.get("updated_at", datetime.now(timezone.utc).isoformat()),
            detail=payload.get("detail", prev.detail),
        )
    return merged


def organ_state_from_verdict(verdict: str) -> OrganState:
    v = str(verdict or "").upper()
    if v.startswith("RED"):
        return "error"
    if v.startswith("YELLOW"):
        return "waiting"
    if "ACTIVE" in v or "RUNNING" in v:
        return "active"
    return "idle"


__all__ = ["KNOWN_ORGANS", "default_organ_map", "merge_organ_events", "organ_state_from_verdict"]
