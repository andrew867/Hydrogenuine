"""PLT operator surface polish descriptors — static fixtures only."""

from __future__ import annotations

from hg_core.exciton_cluster.errors import EXCITON_PLT_SURFACE_RECORDED
from hg_core.exciton_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_product_surface.fixtures import load_plt_surface_fixtures
from hg_runtime.operator_product_surface.types import FIXTURE_CLOCK, plt_surface_from_fixture


def load_plt_polish_descriptors(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Load static PLT v1 surface polish descriptors after PRES/TRB/SIL boundaries."""
    fixtures = load_plt_surface_fixtures()
    descriptors = [plt_surface_from_fixture(row).to_payload() for row in fixtures]
    all_events_only = all(d.get("writes_events_only") is True for d in descriptors)
    all_panic = all(d.get("panic_banner_required") is True for d in descriptors)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": EXCITON_PLT_SURFACE_RECORDED,
        "observed_at": observed_at,
        "surface_count": len(descriptors),
        "writes_events_only": all_events_only,
        "panic_banner_required_all": all_panic,
        "plt_surfaces": descriptors,
        "live_plt_dispatch": False,
        "permission_granted": False,
        "polish_is_not_safety": True,
    }


__all__ = ["load_plt_polish_descriptors"]
