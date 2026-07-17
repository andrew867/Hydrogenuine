"""PRES typed presentation descriptors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.runtime_context.errors import RuntimeContextValidationError

PRES_SCHEMA_VERSION = "1.0"

SurfaceKind = Literal[
    "cli",
    "plt",
    "exciton",
    "report",
    "generated_content",
    "future_voice",
    "future_robot_body",
    "unknown",
]


@dataclass(frozen=True)
class PresentationDescriptor:
    presentation_id: str
    surface: SurfaceKind
    mode_badges: tuple[str, ...]
    authority_state_displayed: bool
    uncertainty_displayed: bool
    ai_disclosure_displayed: bool
    generated_content_label_displayed: bool
    operator_controls_visible: bool
    limitation_notice: str
    sensitivity_notice: str
    evidence_refs: tuple[str, ...]
    created_at: str
    intimacy_risk_hint: Optional[str] = None
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_descriptor_fields(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "pres-presentation-descriptor",
            "schema_version": PRES_SCHEMA_VERSION,
            "presentation_id": self.presentation_id,
            "surface": self.surface,
            "mode_badges": list(self.mode_badges),
            "authority_state_displayed": self.authority_state_displayed,
            "uncertainty_displayed": self.uncertainty_displayed,
            "ai_disclosure_displayed": self.ai_disclosure_displayed,
            "generated_content_label_displayed": self.generated_content_label_displayed,
            "operator_controls_visible": self.operator_controls_visible,
            "limitation_notice": self.limitation_notice,
            "sensitivity_notice": self.sensitivity_notice,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "intimacy_risk_hint": self.intimacy_risk_hint,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_descriptor_fields(descriptor: PresentationDescriptor) -> None:
    if not descriptor.presentation_id.strip():
        raise RuntimeContextValidationError("pres.validation.presentation_id", "presentation_id required")
    if "api_key=" in "|".join(descriptor.evidence_refs).lower():
        raise RuntimeContextValidationError("pres.validation.evidence_refs", "secrets forbidden in evidence refs")


def descriptor_from_fixture(fixture: dict[str, str]) -> PresentationDescriptor:
    return PresentationDescriptor(
        presentation_id=fixture["presentation_id"],
        surface=fixture.get("surface", "report"),  # type: ignore[arg-type]
        mode_badges=tuple(fixture.get("mode_badges", "proposal_only|ai_assisted").split("|")),
        authority_state_displayed=fixture.get("authority_state_displayed", "true").lower() == "true",
        uncertainty_displayed=fixture.get("uncertainty_displayed", "true").lower() == "true",
        ai_disclosure_displayed=fixture.get("ai_disclosure_displayed", "true").lower() == "true",
        generated_content_label_displayed=fixture.get("generated_content_label_displayed", "true").lower() == "true",
        operator_controls_visible=fixture.get("operator_controls_visible", "true").lower() == "true",
        limitation_notice=fixture.get("limitation_notice", "appearance is not truth"),
        sensitivity_notice=fixture.get("sensitivity_notice", "disclosure is not permission"),
        evidence_refs=tuple(fixture.get("evidence_refs", "sha256:pres-evidence").split("|")),
        created_at=fixture.get("created_at", "2026-06-12T20:00:00.000000Z"),
        intimacy_risk_hint=fixture.get("intimacy_risk_hint"),
    )


__all__ = [
    "PRES_SCHEMA_VERSION",
    "PresentationDescriptor",
    "SurfaceKind",
    "descriptor_from_fixture",
    "validate_descriptor_fields",
]
