"""OPB neighbor advisory routing manifest — FW-OPB-05/06 static fixture integration."""

from __future__ import annotations

from hg_core.opb_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_power_boundary.types import FIXTURE_CLOCK


_NEIGHBOR_ROUTES = (
    ("SIL", "silence_discipline_advisory"),
    ("TRB_CAL", "trust_calibration_advisory"),
    ("DEP_BOND", "attachment_risk_advisory"),
    ("AFC", "affective_pressure_advisory"),
    ("MOR", "mortality_shutdown_advisory"),
    ("CNT", "continuity_snapshot_advisory"),
    ("RET", "retention_snapshot_recommendation"),
)


def load_neighbor_advisory_manifest(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Static advisory routing manifest; routes inform only, never block."""
    routes = [
        {
            "target": target,
            "purpose": purpose,
            "route_is_advisory_only": True,
            "permission_granted": False,
            "live_dispatch": False,
        }
        for target, purpose in _NEIGHBOR_ROUTES
    ]
    ret_rec = next(r for r in routes if r["target"] == "RET")
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "opb.advisory.neighbor_routes_manifest",
        "observed_at": observed_at,
        "route_count": len(routes),
        "routes": routes,
        "retention_recommendation_only": ret_rec["purpose"],
        "operator_authority_preserved": True,
        "permission_granted": False,
    }


__all__ = ["load_neighbor_advisory_manifest"]
