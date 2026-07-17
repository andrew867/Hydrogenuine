"""FCE frontier capability evaluation — advisory classification only (FULL BUILD)."""

from hg_runtime.frontier_capability_evaluation.classifier import classify_fixture, classify_fixture_mapping
from hg_runtime.frontier_capability_evaluation.policy import evaluate_capability
from hg_runtime.frontier_capability_evaluation.replay_audit import audit_fce_events
from hg_runtime.frontier_capability_evaluation.routing import route_advisory
from hg_runtime.frontier_capability_evaluation.service import process_signal, process_signal_mapping
from hg_runtime.frontier_capability_evaluation.types import CapabilityEvalResult, FrontierCapabilitySignal

__all__ = [
    "CapabilityEvalResult",
    "FrontierCapabilitySignal",
    "audit_fce_events",
    "classify_fixture",
    "classify_fixture_mapping",
    "evaluate_capability",
    "process_signal",
    "process_signal_mapping",
    "route_advisory",
]
