"""ORI boundary-organ fixture-route integration — slice 4, receipts non-authority."""

from __future__ import annotations

from typing import Any

from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_review_intake.evaluator import analyze_fixture_bundle, intake_review_request
from hg_runtime.operator_review_intake.intake_fixtures import fixture_requests_for_sources
from hg_runtime.operator_review_intake.types import FIXTURE_CLOCK, receipt_from_fixture
from hg_runtime.operator_review_intake.validator import evaluate_operator_review_receipt


def integrate_fixture_routes(
    bundle: dict[str, Any] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """End-to-end OPB/IPB/ARB/EGI fixture routes into ORI intake with non-authority receipts."""
    analysis = analyze_fixture_bundle(bundle, observed_at=observed_at)
    routes: list[dict[str, object]] = []
    for source in ("OPB", "IPB", "ARB", "EGI"):
        for request in fixture_requests_for_sources(source):
            intake = intake_review_request(request, observed_at=observed_at)
            receipt = receipt_from_fixture(
                {
                    "receipt_id": f"ori-integration-{request.review_request_id}",
                    "review_item_ref": f"ori-item:{request.review_request_id}",
                    "operator_action": "deferred",
                }
            )
            evaluated = evaluate_operator_review_receipt(receipt, observed_at=observed_at)
            routes.append(
                {
                    "source_module": source,
                    "review_request_id": request.review_request_id,
                    "intake_status": intake.get("status"),
                    "receipt_status": evaluated.get("status"),
                    "permission_granted": False,
                    "authority_created": False,
                    "receipt_is_not_permit": evaluated.get("permission_granted") is False,
                }
            )
    all_non_authority = all(r.get("permission_granted") is False for r in routes)
    return {
        **advisory_only_marker(),
        "status": "integrated",
        "reason_code": "ori.advisory.fixture_routes_integrated",
        "fixture_integration_only": True,
        "observed_at": observed_at,
        "source_modules": analysis.get("source_modules"),
        "route_count": len(routes),
        "routes": routes,
        "all_receipts_non_authority": all_non_authority,
        "permission_granted": False,
    }


__all__ = ["integrate_fixture_routes"]
