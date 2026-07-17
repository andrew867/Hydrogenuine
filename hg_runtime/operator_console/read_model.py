"""Operator Console Read Model — high-level assembly and validation.

Combines builder functions to produce a complete read model.
The console is read-only and grants no authority.
"""

from __future__ import annotations

from .read_model_schema import (
    SCHEMA_VERSION,
    _INVARIANTS,
)
from .read_model_builder import (
    create_read_model,
    add_section,
    build_status_section,
    build_queue_section,
    build_alert_section,
    build_recommendation_section,
)


def build_full_read_model(
    *,
    run_id: str = "",
    active_run_id: str = "",
    last_completed_run_id: str = "",
    current_verdict: str = "",
    stop_panic_active: bool = False,
    latest_checkin_path: str = "",
    source_candidates: int = 0,
    claims_pending: int = 0,
    quarantined_candidates: int = 0,
    unresolved_contradictions: int = 0,
    weak_outputs: int = 0,
    alerts: list | None = None,
    recommendations: list | None = None,
) -> dict:
    """Build a complete operator console read model with all sections.

    Assembles status, queue, alert, and recommendation sections.
    Returns a read model dict with all invariants enforced.
    """
    model = create_read_model(run_id=run_id)

    # Status section
    status_data = build_status_section(
        active_run_id=active_run_id,
        last_completed_run_id=last_completed_run_id,
        current_verdict=current_verdict,
        stop_panic_active=stop_panic_active,
        latest_checkin_path=latest_checkin_path,
    )
    model = add_section(
        model,
        section_id="status",
        title="System Status",
        section_type="status",
        data=status_data,
    )

    # Queue section
    queue_data = build_queue_section(
        source_candidates=source_candidates,
        claims_pending=claims_pending,
        quarantined_candidates=quarantined_candidates,
        unresolved_contradictions=unresolved_contradictions,
        weak_outputs_needing_retry=weak_outputs,
    )
    model = add_section(
        model,
        section_id="queue",
        title="Processing Queue",
        section_type="queue",
        data=queue_data,
    )

    # Alert section
    alert_data = build_alert_section(alerts=alerts)
    model = add_section(
        model,
        section_id="alerts",
        title="Alerts",
        section_type="alert",
        data=alert_data,
    )

    # Recommendation section
    rec_data = build_recommendation_section(recommendations=recommendations)
    model = add_section(
        model,
        section_id="recommendations",
        title="Recommendations",
        section_type="recommendation",
        data=rec_data,
    )

    return model


def validate_read_model(model: dict) -> list[str]:
    """Validate read model invariants and schema version.

    Returns list of errors (empty = valid).
    """
    errors = []

    if model.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, got {model.get('schema')}"
        )

    for key, expected in _INVARIANTS.items():
        actual = model.get(key)
        if actual is not expected:
            errors.append(f"{key} must be {expected}, got {actual}")

    return errors
