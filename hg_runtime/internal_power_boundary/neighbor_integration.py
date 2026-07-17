"""IPB neighbor fixture integration — TRB/AFC/ADM/TIM advisory routes only."""

from __future__ import annotations

from typing import Any

from hg_core.ipb_cluster.errors import (
    IPB_ADM_PANIC_RULE_RECORDED,
    IPB_NEIGHBOR_ROUTES_INTEGRATED,
    IPB_TIM_EXPIRY_SYNCED,
)
from hg_core.ipb_cluster.no_authority import advisory_only_marker
from hg_runtime.internal_power_boundary.fixtures import (
    load_adm_panic_fixture,
    load_neighbor_fixture_routes,
    load_tim_expiry_fixture,
)
from hg_runtime.internal_power_boundary.types import FIXTURE_CLOCK


def integrate_trb_afc_advisory_routes(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """FW-IPB-05 — TRB/CAL and AFC advisory fixture routes; no live routing."""
    routes: list[dict[str, object]] = []
    for fixture in load_neighbor_fixture_routes():
        routes.append(
            {
                "route_id": fixture["route_id"],
                "neighbor": fixture["neighbor"],
                "signal": fixture["signal"],
                "decision_ref": fixture["decision_ref"],
                "advisory_only": True,
                "live_routing": False,
                "permission_granted": False,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "integrated",
        "reason_code": IPB_NEIGHBOR_ROUTES_INTEGRATED,
        "fixture_integration_only": True,
        "observed_at": observed_at,
        "route_count": len(routes),
        "routes": routes,
        "live_routing": False,
        "permission_granted": False,
    }


def integrate_adm_panic_fixture(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """FW-IPB-06 — ADM panic-rule degraded-mode fixture; no live panic dispatch."""
    fixture = load_adm_panic_fixture()
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": IPB_ADM_PANIC_RULE_RECORDED,
        "fixture_integration_only": True,
        "observed_at": observed_at,
        "panic_rule": fixture["panic_rule"],
        "trigger_count": fixture["trigger_count"],
        "decision_ref": fixture["decision_ref"],
        "degraded_mode": fixture["degraded_mode"],
        "live_panic_dispatch": False,
        "permission_granted": False,
    }


def sync_tim_expiry_fixture(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """FW-IPB-07 — TIM expiry fixture sync for envelopes; no live TIM calls."""
    fixture = load_tim_expiry_fixture()
    expired = observed_at > str(fixture["expires_at"])
    return {
        **advisory_only_marker(),
        "status": "synced",
        "reason_code": IPB_TIM_EXPIRY_SYNCED,
        "fixture_integration_only": True,
        "observed_at": observed_at,
        "envelope_id": fixture["envelope_id"],
        "expires_at": fixture["expires_at"],
        "tim_sync_status": fixture["tim_sync_status"],
        "envelope_expired": expired,
        "live_tim_call": False,
        "permission_granted": False,
    }


def integrate_neighbor_fixture_routes(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """End-to-end neighbor fixture routes — all advisory, non-authority."""
    trb_afc = integrate_trb_afc_advisory_routes(observed_at=observed_at)
    adm = integrate_adm_panic_fixture(observed_at=observed_at)
    tim = sync_tim_expiry_fixture(observed_at=observed_at)
    integrations = [trb_afc, adm, tim]
    all_non_authority = all(i.get("permission_granted") is False for i in integrations)
    return {
        **advisory_only_marker(),
        "status": "integrated",
        "reason_code": IPB_NEIGHBOR_ROUTES_INTEGRATED,
        "fixture_integration_only": True,
        "observed_at": observed_at,
        "integration_count": len(integrations),
        "trb_afc_routes": trb_afc.get("routes"),
        "adm_panic_rule": adm.get("panic_rule"),
        "tim_expiry_sync": tim.get("tim_sync_status"),
        "all_integrations_non_authority": all_non_authority,
        "permission_granted": False,
    }


__all__ = [
    "integrate_adm_panic_fixture",
    "integrate_neighbor_fixture_routes",
    "integrate_trb_afc_advisory_routes",
    "sync_tim_expiry_fixture",
]
