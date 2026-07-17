"""ERB seven-boundary-cluster fixture integration — slice 4, no live external calls."""

from __future__ import annotations

from typing import Any

from hg_core.erb_cluster.no_authority import advisory_only_marker
from hg_runtime.external_relation_boundary.evaluator import analyze_fixture_bundles, route_relation_bundle
from hg_runtime.external_relation_boundary.types import FIXTURE_CLOCK, context_from_fixture, entity_from_fixture

_SEVEN_BOUNDARY_SOURCES = ("OPB", "IPB", "ARB", "ORI", "EGI", "IMB", "ERB")

_CLUSTER_RELATIONS: dict[str, dict[str, Any]] = {
    "OPB": {
        "entity": {"entity_ref_id": "erb-cluster-opb", "entity_type": "operator"},
        "context": {
            "relation_context_id": "erb-ctx-cluster-opb",
            "relation_mode": "operator_control",
            "sensitivity": "internal",
        },
    },
    "IPB": {
        "entity": {"entity_ref_id": "erb-cluster-ipb", "entity_type": "remote_service"},
        "context": {
            "relation_context_id": "erb-ctx-cluster-ipb",
            "relation_mode": "tool_provider",
            "sensitivity": "internal",
        },
    },
    "ARB": {
        "entity": {"entity_ref_id": "erb-cluster-arb", "entity_type": "peer_agent"},
        "context": {
            "relation_context_id": "erb-ctx-cluster-arb",
            "relation_mode": "peer_agent_interaction",
            "sensitivity": "internal",
        },
    },
    "ORI": {
        "entity": {"entity_ref_id": "erb-cluster-ori", "entity_type": "user"},
        "context": {
            "relation_context_id": "erb-ctx-cluster-ori",
            "relation_mode": "conversation",
            "sensitivity": "internal",
        },
    },
    "EGI": {
        "entity": {"entity_ref_id": "erb-cluster-egi", "entity_type": "api_provider"},
        "context": {
            "relation_context_id": "erb-ctx-cluster-egi",
            "relation_mode": "tool_provider",
            "sensitivity": "internal",
        },
    },
    "IMB": {
        "entity": {"entity_ref_id": "erb-cluster-imb", "entity_type": "peer_agent"},
        "context": {
            "relation_context_id": "erb-ctx-cluster-imb",
            "relation_mode": "peer_agent_interaction",
            "sensitivity": "internal",
        },
    },
    "ERB": {
        "entity": {"entity_ref_id": "erb-cluster-erb", "entity_type": "source"},
        "context": {
            "relation_context_id": "erb-ctx-cluster-erb",
            "relation_mode": "citation_source",
            "sensitivity": "public",
        },
    },
}


def integrate_fixture_routes(
    bundle: dict[str, Any] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """End-to-end seven-boundary-cluster fixture routes through ERB with non-authority receipts."""
    analysis = analyze_fixture_bundles(observed_at=observed_at)
    routes: list[dict[str, object]] = []
    for source in _SEVEN_BOUNDARY_SOURCES:
        spec = _CLUSTER_RELATIONS[source]
        entity = entity_from_fixture(spec["entity"])
        context = context_from_fixture(spec["context"], entity_ref_id=entity.entity_ref_id)
        routed = route_relation_bundle(entity, context, observed_at=observed_at)
        receipt = routed.get("receipt")
        receipt_permission = receipt.get("permission_granted") if isinstance(receipt, dict) else None
        route = routed.get("route", {})
        routes.append(
            {
                "source_module": source,
                "entity_ref_id": entity.entity_ref_id,
                "route_status": routed.get("status"),
                "decision_class": route.get("decision_class") if isinstance(route, dict) else None,
                "permission_granted": False,
                "authority_created": False,
                "receipt_is_not_permit": receipt_permission is False or receipt_permission is None,
            }
        )
    all_non_authority = all(r.get("permission_granted") is False for r in routes)
    return {
        **advisory_only_marker(),
        "status": "integrated",
        "reason_code": "erb.advisory.fixture_routes_integrated",
        "fixture_integration_only": True,
        "observed_at": observed_at,
        "bundle_count": analysis.get("bundle_count"),
        "source_modules": list(_SEVEN_BOUNDARY_SOURCES),
        "route_count": len(routes),
        "routes": routes,
        "all_receipts_non_authority": all_non_authority,
        "live_external_call": False,
        "permission_granted": False,
    }


__all__ = ["integrate_fixture_routes"]
