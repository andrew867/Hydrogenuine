"""IMB mediation digest fixture — slice 3, digest is not authority."""

from __future__ import annotations

from hg_core.imb_cluster.errors import IMB_MEDIATION_RECORDED
from hg_core.imb_cluster.no_authority import advisory_only_marker
from hg_runtime.internal_mediation_boundary.evaluator import analyze_fixture_bundles
from hg_runtime.internal_mediation_boundary.types import FIXTURE_CLOCK


def render_mediation_digest_fixture(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Build operator-visible mediation digest from deferred advisory fixture bundles."""
    analysis = analyze_fixture_bundles(observed_at=observed_at)
    digest_items: list[dict[str, object]] = []
    for bundle_result in analysis.get("bundle_results", []):
        if not isinstance(bundle_result, dict):
            continue
        result = bundle_result.get("result")
        if not isinstance(result, dict):
            continue
        bundle_id = bundle_result.get("bundle_id")
        for mediation in result.get("mediations", []):
            if not isinstance(mediation, dict):
                continue
            resolution = mediation.get("selected_resolution")
            if resolution in ("route_to_ORI", "route_to_SIL", "route_to_TIM", "route_to_OBT"):
                digest_items.append(
                    {
                        "bundle_id": bundle_id,
                        "selected_resolution": resolution,
                        "presentation_mode": "digest",
                        "mediation_is_not_authority": True,
                        "permission_granted": False,
                    }
                )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": IMB_MEDIATION_RECORDED,
        "digest_fixture_only": True,
        "mediation_is_not_authority": True,
        "observed_at": observed_at,
        "digest_item_count": len(digest_items),
        "digest_items": digest_items,
        "live_mediation_effect": False,
        "permission_granted": False,
    }


__all__ = ["render_mediation_digest_fixture"]
