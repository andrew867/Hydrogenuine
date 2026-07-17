"""ERB runtime — external relation classification is not authority."""

from hg_runtime.external_relation_boundary.evaluator import (
    analyze_fixture_bundles,
    record_external_entity,
    record_relation_context,
    refuse_erb_as_authority,
    replay_fixture_stream,
    route_relation_bundle,
)
from hg_runtime.external_relation_boundary.events import planned_erb_event_refs
from hg_runtime.external_relation_boundary.fixtures import FIXTURE_RELATION_BUNDLES, load_fixture_bundles
from hg_runtime.external_relation_boundary.policies import load_static_routing_policies
from hg_runtime.external_relation_boundary.types import (
    DEFAULT_ENTITY_REF,
    FIXTURE_CLOCK,
    ExternalEntityRef,
    ExternalRelationContext,
    ExternalRelationDecision,
    ExternalRelationReceipt,
    ExternalRelationRisk,
    context_from_fixture,
    entity_from_fixture,
)

__all__ = [
    "DEFAULT_ENTITY_REF",
    "FIXTURE_CLOCK",
    "FIXTURE_RELATION_BUNDLES",
    "ExternalEntityRef",
    "ExternalRelationContext",
    "ExternalRelationDecision",
    "ExternalRelationReceipt",
    "ExternalRelationRisk",
    "analyze_fixture_bundles",
    "context_from_fixture",
    "entity_from_fixture",
    "load_fixture_bundles",
    "load_static_routing_policies",
    "planned_erb_event_refs",
    "record_external_entity",
    "record_relation_context",
    "refuse_erb_as_authority",
    "replay_fixture_stream",
    "route_relation_bundle",
]
