"""VSP vulnerable subject protection — advisory protective handling only."""

from hg_runtime.vulnerable_subject_protection.classifier import classify_fixture_mapping
from hg_runtime.vulnerable_subject_protection.policy import evaluate_protection, refuse_persuasion_use
from hg_runtime.vulnerable_subject_protection.replay_audit import audit_vsp_events
from hg_runtime.vulnerable_subject_protection.routing import route_advisory
from hg_runtime.vulnerable_subject_protection.service import FIXTURE_CLOCK, process_signal
from hg_runtime.vulnerable_subject_protection.types import ProtectionDecision, VulnerabilitySignal

__all__ = [
    "FIXTURE_CLOCK",
    "ProtectionDecision",
    "VulnerabilitySignal",
    "audit_vsp_events",
    "classify_fixture_mapping",
    "evaluate_protection",
    "process_signal",
    "refuse_persuasion_use",
    "route_advisory",
]
