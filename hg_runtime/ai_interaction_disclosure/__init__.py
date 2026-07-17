"""AID — AI Interaction Disclosure (FULL BUILD)."""

from hg_runtime.ai_interaction_disclosure.disclosure import (
    build_disclosure_card,
    detect_missing_disclosure,
    validate_capability_claim,
)
from hg_runtime.ai_interaction_disclosure.mode_card import ModeCard, build_mode_card
from hg_runtime.ai_interaction_disclosure.policy import CapabilityLimitCard, evaluate_disclosure_policy
from hg_runtime.ai_interaction_disclosure.replay_audit import audit_aid_events
from hg_runtime.ai_interaction_disclosure.report import build_status_report
from hg_runtime.ai_interaction_disclosure.service import process_disclosure
from hg_runtime.ai_interaction_disclosure.types import InteractionDisclosure
from hg_runtime.ai_interaction_disclosure.uncertainty import (
    GeneratedContentDisclosure,
    UncertaintyDisclosure,
)

__all__ = [
    "CapabilityLimitCard",
    "GeneratedContentDisclosure",
    "InteractionDisclosure",
    "ModeCard",
    "UncertaintyDisclosure",
    "audit_aid_events",
    "build_disclosure_card",
    "build_mode_card",
    "build_status_report",
    "detect_missing_disclosure",
    "evaluate_disclosure_policy",
    "process_disclosure",
    "validate_capability_claim",
]
