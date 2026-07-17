"""ARB IPB/OPB/EGI fixture-queue bridge — slice 3, no permission routing."""

from __future__ import annotations

from typing import Any

from hg_core.arb_cluster.errors import ARB_FIXTURE_QUEUE_ENQUEUED, ArbValidationError, REFUSED_ARB_AS_AUTHORITY
from hg_core.arb_cluster.no_authority import advisory_only_marker
from hg_runtime.agency_routing_boundary.evaluator import route_agent_signal
from hg_runtime.agency_routing_boundary.fixtures import bridge_fixture_signals, signal_from_parts
from hg_runtime.agency_routing_boundary.types import FIXTURE_CLOCK, agent0_signal_from_fixture

_ORGAN_BY_ROUTE = {
    "local_ipb": "IPB",
    "operator_power_opb": "OPB",
    "infrastructure_gap_egi": "EGI",
}


class FakeBoundaryOrganQueue:
    """In-memory fake queue for boundary-organ deliveries — advisory only."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []

    def enqueue(
        self,
        *,
        target_organ: str,
        signal_id: str,
        route_class: str,
        route_result: dict[str, object],
        treat_as_authority: bool = False,
    ) -> dict[str, object]:
        if treat_as_authority:
            raise ArbValidationError(
                REFUSED_ARB_AS_AUTHORITY,
                "fixture bridge cannot grant authority",
            )
        item = {
            "queue_id": f"arb-bridge-{len(self._items) + 1}",
            "target_organ": target_organ,
            "signal_id": signal_id,
            "route_class": route_class,
            "route_status": route_result.get("status"),
            "enqueued_at": FIXTURE_CLOCK,
            "status": "queued",
            "permission_granted": False,
            "live_routing": False,
        }
        self._items.append(item)
        return {
            **advisory_only_marker(),
            "status": "enqueued",
            "reason_code": ARB_FIXTURE_QUEUE_ENQUEUED,
            "queue_item": item,
            "queue_depth": len(self._items),
            "fixture_bridge_only": True,
            "permission_granted": False,
        }

    @property
    def depth(self) -> int:
        return len(self._items)


def bridge_fixture_queues(
    signals: tuple[dict[str, str], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Route fixture signals to IPB/OPB/EGI fake queues — bridge only."""
    active = signals if signals is not None else bridge_fixture_signals()
    queue = FakeBoundaryOrganQueue()
    enqueued: list[dict[str, object]] = []
    for row in active:
        fixture = signal_from_parts(row)
        signal = agent0_signal_from_fixture(fixture)
        routed = route_agent_signal(signal, observed_at=observed_at)
        route_class = str(routed.get("route_class", "unknown_fail_closed"))
        target_organ = _ORGAN_BY_ROUTE.get(route_class)
        if target_organ is None:
            continue
        enqueued.append(
            queue.enqueue(
                target_organ=target_organ,
                signal_id=signal.signal_id,
                route_class=route_class,
                route_result=routed,
            )
        )
    return {
        **advisory_only_marker(),
        "status": "bridged",
        "fixture_bridge_only": True,
        "queue_depth": queue.depth,
        "enqueued": enqueued,
        "target_organs": sorted({item["queue_item"]["target_organ"] for item in enqueued}),  # type: ignore[index]
        "permission_granted": False,
    }


__all__ = ["FakeBoundaryOrganQueue", "bridge_fixture_queues"]
