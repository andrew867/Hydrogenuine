"""DRB dream reflection boundary — fixture/static only, no live memory mutation."""

from hg_runtime.dream_reflection_boundary.evaluator import (
    analyze_fixture_bundles,
    consolidate_fragments,
    create_counterfactual_scenario,
    create_dream_fragments,
    create_reflection_receipt,
    process_reflection_bundle,
    record_reflection_request,
    refuse_drb_as_authority,
)
from hg_runtime.dream_reflection_boundary.events import planned_drb_event_refs
from hg_runtime.dream_reflection_boundary.fixtures import load_fixture_bundles
from hg_runtime.dream_reflection_boundary.replay import replay_fixture_stream
from hg_runtime.dream_reflection_boundary.types import (
    FIXTURE_CLOCK,
    ConsolidationDecision,
    CounterfactualScenario,
    DreamFragment,
    DreamReflectionReceipt,
    DreamReflectionRequest,
    classify_reflection_claim_risk,
    reflection_request_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "ConsolidationDecision",
    "CounterfactualScenario",
    "DreamFragment",
    "DreamReflectionReceipt",
    "DreamReflectionRequest",
    "analyze_fixture_bundles",
    "classify_reflection_claim_risk",
    "consolidate_fragments",
    "create_counterfactual_scenario",
    "create_dream_fragments",
    "create_reflection_receipt",
    "load_fixture_bundles",
    "planned_drb_event_refs",
    "process_reflection_bundle",
    "record_reflection_request",
    "reflection_request_from_fixture",
    "refuse_drb_as_authority",
    "replay_fixture_stream",
]
