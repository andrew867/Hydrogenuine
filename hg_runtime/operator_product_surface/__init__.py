"""Operator product surface — Batch P7-A, all slices, no native UI."""

from hg_runtime.operator_product_surface.audit import audit_surface_polish_claims
from hg_runtime.operator_product_surface.backburner import (
    assert_exciton_backburner_boundary,
    refuse_native_ui_off_backburner,
)
from hg_runtime.operator_product_surface.events import planned_exciton_event_refs
from hg_runtime.operator_product_surface.fixtures import load_fixture_bundles, load_plt_surface_fixtures
from hg_runtime.operator_product_surface.plt import load_plt_polish_descriptors
from hg_runtime.operator_product_surface.proposal import (
    dispatch_authority_chain_proposal,
    refuse_action_as_permission,
)
from hg_runtime.operator_product_surface.queue import FakeOperatorActionQueue, enqueue_fixture_queue
from hg_runtime.operator_product_surface.router import analyze_fixture_bundles, route_operator_bundle
from hg_runtime.operator_product_surface.types import (
    FIXTURE_CLOCK,
    ActionDecision,
    OperatorActionRequest,
    OperatorSurfaceDescriptor,
    PltSurfacePolishDescriptor,
    PolishAssessment,
    action_request_from_fixture,
    plt_surface_from_fixture,
    surface_descriptor_from_fixture,
)

__all__ = [
    "ActionDecision",
    "FIXTURE_CLOCK",
    "FakeOperatorActionQueue",
    "OperatorActionRequest",
    "OperatorSurfaceDescriptor",
    "PltSurfacePolishDescriptor",
    "PolishAssessment",
    "action_request_from_fixture",
    "analyze_fixture_bundles",
    "assert_exciton_backburner_boundary",
    "audit_surface_polish_claims",
    "dispatch_authority_chain_proposal",
    "enqueue_fixture_queue",
    "load_fixture_bundles",
    "load_plt_polish_descriptors",
    "load_plt_surface_fixtures",
    "planned_exciton_event_refs",
    "plt_surface_from_fixture",
    "refuse_action_as_permission",
    "refuse_native_ui_off_backburner",
    "route_operator_bundle",
    "surface_descriptor_from_fixture",
]
