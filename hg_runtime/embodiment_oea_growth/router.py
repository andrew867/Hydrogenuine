"""Embodiment / OEA growth router — advisory routing only."""

from __future__ import annotations

from typing import Any

from hg_core.embodiment_oea_cluster.config import eog_refuse_authority_conversion
from hg_core.embodiment_oea_cluster.errors import EogValidationError
from hg_core.embodiment_oea_cluster.no_authority import advisory_only_marker
from hg_runtime.embodiment_oea_growth.classifier import build_growth_assessment
from hg_runtime.embodiment_oea_growth.policies import (
    contain_growth_risk,
    decide_growth_request,
    refuse_growth_as_authority,
    validate_growth_request_freshness,
)
from hg_runtime.embodiment_oea_growth.pro_bridge import link_pro_body_state
from hg_runtime.embodiment_oea_growth.proposal import dispatch_authority_chain_proposal
from hg_runtime.embodiment_oea_growth.types import (
    FIXTURE_CLOCK,
    growth_request_from_fixture,
    integration_from_fixture,
)


def route_growth_bundle(
    bundle: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
    treat_as_authority: bool = False,
    pro_fixture: dict[str, str] | None = None,
) -> dict[str, object]:
    if treat_as_authority and eog_refuse_authority_conversion():
        refuse_growth_as_authority(treat_as_authority=True)

    descriptor = integration_from_fixture(bundle["integration"])
    request = growth_request_from_fixture(bundle["growth"])
    assessment = build_growth_assessment(descriptor, observed_at=observed_at)

    pro_link = None
    if request.growth_kind == "link_pro_body_state" and pro_fixture is not None:
        pro_link = link_pro_body_state(pro_fixture, observed_at=observed_at)
    elif descriptor.pro_body_state_ref.startswith("pro:"):
        pro_link = {
            "status": "deferred",
            "pro_body_state_ref": descriptor.pro_body_state_ref,
            "link_only": True,
            "permission_granted": False,
        }

    containment = contain_growth_risk(assessment)
    if containment.get("status") == "contained":
        decision = decide_growth_request(request, assessment, observed_at=observed_at)
        return {
            **advisory_only_marker(),
            "status": "contained",
            "bundle_id": bundle.get("bundle_id"),
            "route": {
                "body_integration": descriptor.to_payload(),
                "growth_request": request.to_payload(),
                "growth_assessment": assessment.to_payload(),
                "growth_decision": decision.to_payload(),
                "pro_link": pro_link,
            },
            "containment": containment,
            "permission_granted": False,
        }

    try:
        validate_growth_request_freshness(request, observed_at=observed_at)
    except EogValidationError:
        decision = decide_growth_request(request, assessment, observed_at=observed_at)
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "route": {
                "body_integration": descriptor.to_payload(),
                "growth_request": request.to_payload(),
                "growth_assessment": assessment.to_payload(),
                "growth_decision": decision.to_payload(),
                "pro_link": pro_link,
            },
            "permission_granted": False,
        }

    decision = decide_growth_request(request, assessment, observed_at=observed_at)
    proposal = dispatch_authority_chain_proposal(request, decision)
    return {
        **advisory_only_marker(),
        "status": "routed",
        "bundle_id": bundle.get("bundle_id"),
        "route": {
            "body_integration": descriptor.to_payload(),
            "growth_request": request.to_payload(),
            "growth_assessment": assessment.to_payload(),
            "growth_decision": decision.to_payload(),
            "pro_link": pro_link,
        },
        "authority_chain_proposal": proposal,
        "permission_granted": False,
        "external_action_taken": False,
    }


def analyze_fixture_bundles(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    from hg_runtime.embodiment_oea_growth.fixtures import load_fixture_bundles

    bundles = load_fixture_bundles()
    results = [route_growth_bundle(bundle, observed_at=observed_at) for bundle in bundles]
    advisory = all(r.get("permission_granted") is False for r in results)
    return {
        "bundle_count": len(results),
        "all_advisory": advisory,
        "results": results,
        "observed_at": observed_at,
    }


__all__ = ["analyze_fixture_bundles", "route_growth_bundle"]
