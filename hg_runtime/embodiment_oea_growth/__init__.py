"""Embodiment / OEA growth — Batch P7-B, all slices, no live hardware."""

from hg_runtime.embodiment_oea_growth.audit import audit_embodiment_growth_claims
from hg_runtime.embodiment_oea_growth.backburner import (
    assert_eog_backburner_boundary,
    refuse_hardware_off_backburner,
)
from hg_runtime.embodiment_oea_growth.events import planned_eog_event_refs
from hg_runtime.embodiment_oea_growth.fixtures import (
    load_fixture_bundles,
    load_oea_catalog_fixtures,
    load_pro_body_fixtures,
)
from hg_runtime.embodiment_oea_growth.oea_growth import load_oea_catalog_growth_descriptors
from hg_runtime.embodiment_oea_growth.pro_bridge import link_pro_body_state
from hg_runtime.embodiment_oea_growth.proposal import (
    dispatch_authority_chain_proposal,
    refuse_growth_as_permission,
)
from hg_runtime.embodiment_oea_growth.queue import FakeEmbodimentGrowthQueue, enqueue_fixture_queue
from hg_runtime.embodiment_oea_growth.router import analyze_fixture_bundles, route_growth_bundle
from hg_runtime.embodiment_oea_growth.types import (
    FIXTURE_CLOCK,
    BodyIntegrationDescriptor,
    EmbodimentGrowthRequest,
    GrowthAssessment,
    GrowthDecision,
    OeaCatalogGrowthDescriptor,
    growth_request_from_fixture,
    integration_from_fixture,
)

__all__ = [
    "BodyIntegrationDescriptor",
    "EmbodimentGrowthRequest",
    "FakeEmbodimentGrowthQueue",
    "FIXTURE_CLOCK",
    "GrowthAssessment",
    "GrowthDecision",
    "OeaCatalogGrowthDescriptor",
    "analyze_fixture_bundles",
    "assert_eog_backburner_boundary",
    "audit_embodiment_growth_claims",
    "dispatch_authority_chain_proposal",
    "enqueue_fixture_queue",
    "growth_request_from_fixture",
    "integration_from_fixture",
    "link_pro_body_state",
    "load_fixture_bundles",
    "load_oea_catalog_fixtures",
    "load_oea_catalog_growth_descriptors",
    "load_pro_body_fixtures",
    "planned_eog_event_refs",
    "refuse_growth_as_permission",
    "refuse_hardware_off_backburner",
    "route_growth_bundle",
]
