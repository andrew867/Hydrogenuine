"""OEA catalog growth descriptors — static fixtures only."""

from __future__ import annotations

from hg_core.embodiment_oea_cluster.errors import EOG_OEA_CATALOG_RECORDED
from hg_core.embodiment_oea_cluster.no_authority import advisory_only_marker
from hg_runtime.embodiment_oea_growth.fixtures import load_oea_catalog_fixtures
from hg_runtime.embodiment_oea_growth.types import FIXTURE_CLOCK, catalog_entry_from_fixture


def load_oea_catalog_growth_descriptors(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Load static OEA catalog growth descriptors bounded by GPP/UEAK/SOAR."""
    fixtures = load_oea_catalog_fixtures()
    entries = [catalog_entry_from_fixture(row).to_payload() for row in fixtures]
    all_bounded = all(e.get("bounded_by_gpp_ueak") is True for e in entries)
    all_soar = all(e.get("soar_review_required") is True for e in entries)
    all_events_only = all(e.get("writes_events_only") is True for e in entries)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": EOG_OEA_CATALOG_RECORDED,
        "observed_at": observed_at,
        "entry_count": len(entries),
        "bounded_by_gpp_ueak_all": all_bounded,
        "soar_review_required_all": all_soar,
        "writes_events_only": all_events_only,
        "catalog_entries": entries,
        "live_oea_dispatch": False,
        "permission_granted": False,
        "catalog_growth_is_not_permission": True,
    }


__all__ = ["load_oea_catalog_growth_descriptors"]
