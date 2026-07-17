"""Operator product surface router — advisory routing only."""

from __future__ import annotations

from typing import Any

from hg_core.exciton_cluster.config import exciton_refuse_authority_conversion
from hg_core.exciton_cluster.errors import ExcitonValidationError
from hg_core.exciton_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_product_surface.classifier import build_polish_assessment
from hg_runtime.operator_product_surface.policies import (
    contain_polish_risk,
    decide_operator_action,
    refuse_surface_as_authority,
    validate_action_request_freshness,
)
from hg_runtime.operator_product_surface.proposal import dispatch_authority_chain_proposal
from hg_runtime.operator_product_surface.types import (
    FIXTURE_CLOCK,
    action_request_from_fixture,
    surface_descriptor_from_fixture,
)


def route_operator_bundle(
    bundle: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority and exciton_refuse_authority_conversion():
        refuse_surface_as_authority(treat_as_authority=True)

    descriptor = surface_descriptor_from_fixture(bundle["surface"])
    request = action_request_from_fixture(bundle["action"])
    assessment = build_polish_assessment(descriptor, observed_at=observed_at)

    containment = contain_polish_risk(assessment)
    if containment.get("status") == "contained":
        decision = decide_operator_action(request, assessment, observed_at=observed_at)
        return {
            **advisory_only_marker(),
            "status": "contained",
            "bundle_id": bundle.get("bundle_id"),
            "route": {
                "surface_descriptor": descriptor.to_payload(),
                "action_request": request.to_payload(),
                "polish_assessment": assessment.to_payload(),
                "action_decision": decision.to_payload(),
            },
            "containment": containment,
            "permission_granted": False,
        }

    try:
        validate_action_request_freshness(request, observed_at=observed_at)
    except ExcitonValidationError:
        decision = decide_operator_action(request, assessment, observed_at=observed_at)
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "route": {
                "surface_descriptor": descriptor.to_payload(),
                "action_request": request.to_payload(),
                "polish_assessment": assessment.to_payload(),
                "action_decision": decision.to_payload(),
            },
            "permission_granted": False,
        }

    decision = decide_operator_action(request, assessment, observed_at=observed_at)
    proposal = dispatch_authority_chain_proposal(request, decision)
    return {
        **advisory_only_marker(),
        "status": "routed",
        "bundle_id": bundle.get("bundle_id"),
        "route": {
            "surface_descriptor": descriptor.to_payload(),
            "action_request": request.to_payload(),
            "polish_assessment": assessment.to_payload(),
            "action_decision": decision.to_payload(),
        },
        "authority_chain_proposal": proposal,
        "permission_granted": False,
        "external_action_taken": False,
    }


def analyze_fixture_bundles(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    from hg_runtime.operator_product_surface.fixtures import load_fixture_bundles

    bundles = load_fixture_bundles()
    results = [route_operator_bundle(bundle, observed_at=observed_at) for bundle in bundles]
    advisory = all(r.get("permission_granted") is False for r in results)
    return {
        "bundle_count": len(results),
        "all_advisory": advisory,
        "results": results,
        "observed_at": observed_at,
    }


__all__ = ["analyze_fixture_bundles", "route_operator_bundle"]
