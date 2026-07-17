"""IMB seven-boundary-cluster fixture integration — slice 4, receipts non-authority."""

from __future__ import annotations

from typing import Any

from hg_core.imb_cluster.no_authority import advisory_only_marker
from hg_runtime.internal_mediation_boundary.evaluator import analyze_fixture_bundles, mediate_claim_bundle
from hg_runtime.internal_mediation_boundary.types import FIXTURE_CLOCK, module_claim_from_fixture

_SEVEN_BOUNDARY_SOURCES = ("OPB", "IPB", "ARB", "ORI", "EGI", "IMB", "ERB")

_CLUSTER_CLAIMS: dict[str, dict[str, str]] = {
    "OPB": {
        "claim_id": "imb-cluster-opb",
        "source_module": "OPB",
        "claim_type": "operator_review_request",
        "claim_summary": "Operator review pressure from cluster fixture",
    },
    "IPB": {
        "claim_id": "imb-cluster-ipb",
        "source_module": "IPB",
        "claim_type": "route_recommendation",
        "claim_summary": "Internal autonomy route from cluster fixture",
    },
    "ARB": {
        "claim_id": "imb-cluster-arb",
        "source_module": "ARB",
        "claim_type": "route_recommendation",
        "claim_summary": "Agency routing recommendation from cluster fixture",
    },
    "ORI": {
        "claim_id": "imb-cluster-ori",
        "source_module": "ORI",
        "claim_type": "operator_review_request",
        "claim_summary": "Operator review intake signal from cluster fixture",
    },
    "EGI": {
        "claim_id": "imb-cluster-egi",
        "source_module": "EGI",
        "claim_type": "infrastructure_gap",
        "claim_summary": "Infrastructure gap from cluster fixture",
    },
    "IMB": {
        "claim_id": "imb-cluster-imb",
        "source_module": "Agent0",
        "claim_type": "route_recommendation",
        "claim_summary": "Internal mediation advisory from cluster fixture",
    },
    "ERB": {
        "claim_id": "imb-cluster-erb",
        "source_module": "Agent0",
        "claim_type": "risk_observation",
        "claim_summary": "External relation advisory from cluster fixture",
    },
}


def integrate_fixture_routes(
    bundle: dict[str, Any] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """End-to-end seven-boundary-cluster fixture routes into IMB mediation with non-authority receipts."""
    analysis = analyze_fixture_bundles(observed_at=observed_at)
    routes: list[dict[str, object]] = []
    for source in _SEVEN_BOUNDARY_SOURCES:
        claim = module_claim_from_fixture(_CLUSTER_CLAIMS[source])
        mediation = mediate_claim_bundle((claim,), observed_at=observed_at)
        receipts = mediation.get("receipts", [])
        receipt_status = receipts[0].get("permission_granted") if receipts else None
        routes.append(
            {
                "source_module": source,
                "claim_id": claim.claim_id,
                "mediation_status": mediation.get("status"),
                "receipt_status": receipt_status,
                "permission_granted": False,
                "authority_created": False,
                "receipt_is_not_permit": receipt_status is False or receipt_status is None,
            }
        )
    all_non_authority = all(r.get("permission_granted") is False for r in routes)
    return {
        **advisory_only_marker(),
        "status": "integrated",
        "reason_code": "imb.advisory.fixture_routes_integrated",
        "fixture_integration_only": True,
        "observed_at": observed_at,
        "bundle_count": analysis.get("bundle_count"),
        "source_modules": list(_SEVEN_BOUNDARY_SOURCES),
        "route_count": len(routes),
        "routes": routes,
        "all_receipts_non_authority": all_non_authority,
        "permission_granted": False,
    }


__all__ = ["integrate_fixture_routes"]
