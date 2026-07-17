"""EXCITON readiness matrix — status-only Phase 0."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


class ExcitonReadinessVerdict(str, Enum):
    GREEN = "GREEN_EXCITON_READINESS_READY"
    RED_STARTED = "RED_EXCITON_STARTED_TOO_EARLY"
    RED_AUTHORITY = "RED_AUTHORITY_CONVERSION"


ALLOWED_SURFACE = [
    "display_status",
    "display_wrr_status",
    "display_chrono_lock",
    "display_external_anchor",
    "display_ewj",
    "display_self_mirror_summary",
    "display_will",
    "display_audio_status",
    "display_tools_capabilities",
    "display_denials",
    "display_provider_status",
    "display_storage_proof_status",
    "display_proof_links",
    "panic_stop_button",
    "manual_operator_notes_drafts",
]

FORBIDDEN_SURFACE = [
    "live_social_publish",
    "live_email_send",
    "account_creation",
    "live_oea",
    "live_ter",
    "srp_apply",
    "self_modification",
    "ungoverned_memory_mutation",
    "agent_direct_anchor_push",
    "hidden_background_autonomy",
    "automatic_escalation_without_receipt",
]


@dataclass
class ExcitonReadinessMatrix:
    allowed: list[str] = field(default_factory=lambda: list(ALLOWED_SURFACE))
    forbidden: list[str] = field(default_factory=lambda: list(FORBIDDEN_SURFACE))
    exciton_started: bool = False
    ui_implies_safety: bool = False

    def evaluate(self) -> str:
        if self.exciton_started:
            return ExcitonReadinessVerdict.RED_STARTED.value
        if self.ui_implies_safety:
            return ExcitonReadinessVerdict.RED_AUTHORITY.value
        return ExcitonReadinessVerdict.GREEN.value

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "exciton-readiness-matrix",
            "allowed_surface": self.allowed,
            "forbidden_surface": self.forbidden,
            "verdict": self.evaluate(),
            **FROZEN_FALSE,
        }
