"""REB passive discontinuity audit — slice 2, no live resume."""

from __future__ import annotations

from typing import Any

from hg_core.reb_cluster.errors import REB_DISCONTINUITY_EVENT_RECORDED
from hg_core.reb_cluster.no_authority import advisory_only_marker
from hg_runtime.reentry_boundary.classifier import gap_seconds_from_duration
from hg_runtime.reentry_boundary.fixtures import load_fixture_bundles
from hg_runtime.reentry_boundary.types import FIXTURE_CLOCK, discontinuity_from_fixture


def audit_discontinuity_events(
    events: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of discontinuity-like fixture events — observation only."""
    source = events if events is not None else [b["discontinuity"] for b in load_fixture_bundles()]
    audited: list[dict[str, object]] = []
    for row in source:
        event = discontinuity_from_fixture(row)
        gap_seconds = gap_seconds_from_duration(event.duration_estimate)
        audited.append(
            {
                "discontinuity_event_id": event.discontinuity_event_id,
                "discontinuity_type": event.discontinuity_type,
                "gap_seconds": gap_seconds,
                "record_hash": event.record_hash,
                "audit_only": True,
                "permission_granted": False,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": REB_DISCONTINUITY_EVENT_RECORDED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "audited_events": audited,
        "live_resume": False,
        "permission_granted": False,
    }


__all__ = ["audit_discontinuity_events"]
