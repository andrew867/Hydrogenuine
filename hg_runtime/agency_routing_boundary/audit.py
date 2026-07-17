"""ARB passive routing audit — slice 2, RTC replay observation only."""

from __future__ import annotations

from typing import Any

from hg_core.arb_cluster.errors import ARB_ROUTE_EVENT_RECORDED
from hg_core.arb_cluster.no_authority import advisory_only_marker
from hg_runtime.agency_routing_boundary.evaluator import route_agent_signal
from hg_runtime.agency_routing_boundary.fixtures import load_fixture_signals, signal_from_parts
from hg_runtime.agency_routing_boundary.types import FIXTURE_CLOCK, agent0_signal_from_fixture


def audit_route_events(
    events: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of route-like fixture events — observation only."""
    source = events if events is not None else [signal_from_parts(row) for row in load_fixture_signals()]
    audited: list[dict[str, object]] = []
    for row in source:
        signal = agent0_signal_from_fixture(row)
        routed = route_agent_signal(signal, observed_at=observed_at)
        decision = routed.get("decision")
        record_hash = decision.get("record_hash", "") if isinstance(decision, dict) else ""
        audited.append(
            {
                "signal_id": signal.signal_id,
                "source_layer": signal.source_layer,
                "signal_type": signal.signal_type,
                "route_class": routed.get("route_class"),
                "status": routed.get("status"),
                "record_hash": record_hash,
                "audit_only": True,
                "permission_granted": False,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": ARB_ROUTE_EVENT_RECORDED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "audited_events": audited,
        "live_routing": False,
        "permission_granted": False,
    }


__all__ = ["audit_route_events"]
