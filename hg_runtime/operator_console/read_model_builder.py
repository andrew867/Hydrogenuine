"""Operator Console Read Model builder — immutable model construction.

Every mutation returns a new model dict. Invariants are re-applied on
every operation. The console is read-only and grants no authority.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from .read_model_schema import (
    SCHEMA_VERSION,
    SECTION_TYPES,
    _INVARIANTS,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_read_model(*, run_id: str = "", timestamp: str = "") -> dict:
    """Create an empty operator console read model.

    The model is a read-only projection — it never changes system state.
    """
    return {
        "schema": SCHEMA_VERSION,
        "run_id": run_id,
        "timestamp": timestamp or _utc_now_iso(),
        "sections": {},
        **copy.deepcopy(_INVARIANTS),
    }


def add_section(
    model: dict,
    *,
    section_id: str,
    title: str,
    section_type: str,
    data: dict,
) -> dict:
    """Add a section to the read model. Returns new model.

    section_type must be in SECTION_TYPES. Raises ValueError if invalid.
    """
    if section_type not in SECTION_TYPES:
        raise ValueError(
            f"Invalid section_type '{section_type}'. "
            f"Must be one of: {sorted(SECTION_TYPES)}"
        )

    section = {
        "section_id": section_id,
        "title": title,
        "section_type": section_type,
        "data": data,
        "added_at": _utc_now_iso(),
    }

    model = dict(model)
    model["sections"] = dict(model.get("sections", {}))
    model["sections"][section_id] = section

    # Re-enforce invariants
    model.update(copy.deepcopy(_INVARIANTS))

    return model


def build_status_section(
    *,
    active_run_id: str = "",
    last_completed_run_id: str = "",
    current_verdict: str = "",
    stop_panic_active: bool = False,
    latest_checkin_path: str = "",
) -> dict:
    """Build data dict for a 'status' section."""
    return {
        "active_run_id": active_run_id,
        "last_completed_run_id": last_completed_run_id,
        "current_verdict": current_verdict,
        "stop_panic_active": stop_panic_active,
        "latest_checkin_path": latest_checkin_path,
    }


def build_queue_section(
    *,
    source_candidates: int = 0,
    claims_pending: int = 0,
    quarantined_candidates: int = 0,
    unresolved_contradictions: int = 0,
    weak_outputs_needing_retry: int = 0,
) -> dict:
    """Build data dict for a 'queue' section."""
    return {
        "source_candidates": source_candidates,
        "claims_pending": claims_pending,
        "quarantined_candidates": quarantined_candidates,
        "unresolved_contradictions": unresolved_contradictions,
        "weak_outputs_needing_retry": weak_outputs_needing_retry,
    }


def build_alert_section(*, alerts: list | None = None) -> dict:
    """Build data dict for an 'alert' section.

    alerts is a list of {"level": "info"|"warning"|"critical", "message": str}.
    """
    return {
        "alerts": alerts or [],
    }


def build_recommendation_section(*, recommendations: list | None = None) -> dict:
    """Build data dict for a 'recommendation' section.

    recommendations is a list of str.
    """
    return {
        "recommendations": recommendations or [],
    }
