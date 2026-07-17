"""ERB disclosure/consent digest fixture — slice 3, digest is not publication."""

from __future__ import annotations

from hg_core.erb_cluster.errors import ERB_CONTEXT_RECORDED
from hg_core.erb_cluster.no_authority import advisory_only_marker
from hg_runtime.external_relation_boundary.evaluator import analyze_fixture_bundles
from hg_runtime.external_relation_boundary.types import FIXTURE_CLOCK


def render_disclosure_consent_digest_fixture(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Build disclosure/consent digest from relation fixture bundles requiring review."""
    analysis = analyze_fixture_bundles(observed_at=observed_at)
    digest_items: list[dict[str, object]] = []
    for bundle_result in analysis.get("bundle_results", []):
        if not isinstance(bundle_result, dict):
            continue
        result = bundle_result.get("result")
        if not isinstance(result, dict):
            continue
        bundle_id = bundle_result.get("bundle_id")
        route = result.get("route")
        if not isinstance(route, dict):
            continue
        decision_class = route.get("decision_class")
        if decision_class in (
            "require_publication_review",
            "require_operator_review",
            "route_to_security_review",
            "cite_source",
        ):
            digest_items.append(
                {
                    "bundle_id": bundle_id,
                    "decision_class": decision_class,
                    "presentation_mode": "disclosure_consent_digest",
                    "consent_is_not_permission": True,
                    "disclosure_is_not_publication": True,
                    "permission_granted": False,
                }
            )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ERB_CONTEXT_RECORDED,
        "digest_fixture_only": True,
        "consent_is_not_permission": True,
        "disclosure_is_not_publication": True,
        "observed_at": observed_at,
        "digest_item_count": len(digest_items),
        "digest_items": digest_items,
        "live_publication_effect": False,
        "permission_granted": False,
    }


__all__ = ["render_disclosure_consent_digest_fixture"]
