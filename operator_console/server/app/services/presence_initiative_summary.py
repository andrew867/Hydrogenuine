from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hg_core.affective.state import get_regulatory_state_snapshot
from hg_core.autonomy_config import get_autonomy_config


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _initiative_mode_from_cadence(cadence_payload: dict[str, Any] | None) -> str:
    if not cadence_payload:
        return "scheduled_only"
    if cadence_payload.get("scheduler_job_id"):
        return "self_timed_override"
    if cadence_payload.get("requested_duration_minutes") or cadence_payload.get("minimum_sleep_minutes"):
        return "bounded_sleep"
    return "scheduled_only"


def build_presence_initiative_summary(
    *,
    root: Path | None,
    task_name: str,
    session_target: str,
    binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding = binding or {}
    if not root:
        return {
            "status": "missing",
            "initiative_mode": "unknown",
            "autonomy_config": {},
            "cadence_request": None,
            "next_earliest_wake_at": None,
            "agency_budget": None,
            "trust_band": None,
        }

    namespace_target = str(binding.get("operational_session_target") or "").strip() or session_target
    namespace_dir = root / "memory" / "automation" / namespace_target if namespace_target else None
    cadence_payload = _read_json(namespace_dir / "cadence_request.json") if namespace_dir else None

    requested_at = _parse_timestamp((cadence_payload or {}).get("requested_at"))
    next_earliest_wake_at = _parse_timestamp((cadence_payload or {}).get("not_before"))
    requested_duration = (cadence_payload or {}).get("requested_duration_minutes")
    if next_earliest_wake_at is None and requested_at and isinstance(requested_duration, int) and requested_duration > 0:
        next_earliest_wake_at = requested_at + timedelta(minutes=requested_duration)

    continuity_anchor = str(binding.get("operational_agent_id") or "").strip() or task_name
    regulatory = get_regulatory_state_snapshot(root, "agent", continuity_anchor, agent_id=continuity_anchor)
    regulatory_state = regulatory.get("state") if isinstance(regulatory, dict) else {}
    regulatory_state = regulatory_state if isinstance(regulatory_state, dict) else {}

    autonomy = get_autonomy_config(root)
    initiative_mode = _initiative_mode_from_cadence(cadence_payload)
    status = "healthy" if cadence_payload or regulatory_state or autonomy else "partial"
    if not cadence_payload and not regulatory_state and not autonomy:
        status = "missing"

    return {
        "status": status,
        "initiative_mode": initiative_mode,
        "continuity_anchor": continuity_anchor,
        "autonomy_config": {
            "entity_dag_change_control": autonomy.get("entity_dag_change_control"),
            "outbound_safety_gate_enabled": autonomy.get("outbound_safety_gate_enabled"),
        },
        "cadence_request": cadence_payload,
        "next_earliest_wake_at": _iso(next_earliest_wake_at),
        "agency_budget": regulatory_state.get("agency_budget"),
        "trust_band": regulatory_state.get("trust_band"),
        "incident_points": regulatory_state.get("incident_points"),
        "escrow_locked": regulatory_state.get("escrow_locked"),
    }
