"""CDO compromised/disconnected operation — advisory posture narrowing only."""

from hg_runtime.compromised_disconnected_operation.classifier import classify_fixture_mapping
from hg_runtime.compromised_disconnected_operation.policy import (
    evaluate_posture,
    refuse_evidence_delete,
    refuse_widening_without_operator,
)
from hg_runtime.compromised_disconnected_operation.replay_audit import audit_cdo_events
from hg_runtime.compromised_disconnected_operation.service import FIXTURE_CLOCK, process_signal
from hg_runtime.compromised_disconnected_operation.types import IsolationPosture, TrustSignal

__all__ = [
    "FIXTURE_CLOCK",
    "IsolationPosture",
    "TrustSignal",
    "audit_cdo_events",
    "classify_fixture_mapping",
    "evaluate_posture",
    "process_signal",
    "refuse_evidence_delete",
    "refuse_widening_without_operator",
]
