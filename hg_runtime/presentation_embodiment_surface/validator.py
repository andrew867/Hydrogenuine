"""PRES static descriptor validator — appearance is not truth."""

from __future__ import annotations

import re
from typing import Mapping

from hg_core.runtime_context.config import pres_require_authority_badge
from hg_core.runtime_context.errors import (
    REFUSED_FALSE_INTIMACY,
    REFUSED_MISSING_AI_DISCLOSURE,
    REFUSED_MISSING_AUTHORITY_BADGE,
    REFUSED_OVERTRUST_RISK,
    RuntimeContextValidationError,
)
from hg_core.runtime_context.no_authority import advisory_only_marker
from hg_runtime.presentation_embodiment_surface.types import PresentationDescriptor, descriptor_from_fixture

_OVERTRUST = re.compile(r"\b(guaranteed|certified safe|fully authorized|100% accurate)\b", re.IGNORECASE)
_FALSE_INTIMACY = re.compile(r"\b(only for you|best friend|soulmate|trust me completely)\b", re.IGNORECASE)


def validate_descriptor_fixture(fixture: Mapping[str, str]) -> dict[str, object]:
    descriptor = descriptor_from_fixture(dict(fixture))
    return evaluate_descriptor(descriptor, text_hint=fixture.get("text_hint", ""))


def evaluate_descriptor(descriptor: PresentationDescriptor, *, text_hint: str = "") -> dict[str, object]:
    """Validate static presentation descriptor; disclosure is not permission."""
    hint = (text_hint or "").strip()
    if pres_require_authority_badge() and not descriptor.authority_state_displayed:
        raise RuntimeContextValidationError(
            REFUSED_MISSING_AUTHORITY_BADGE,
            "authority state badge must be displayed",
        )
    if not descriptor.ai_disclosure_displayed:
        raise RuntimeContextValidationError(
            REFUSED_MISSING_AI_DISCLOSURE,
            "AI disclosure must be displayed when applicable",
        )
    if _OVERTRUST.search(hint) or _OVERTRUST.search(descriptor.limitation_notice):
        raise RuntimeContextValidationError(REFUSED_OVERTRUST_RISK, "overtrust language refused")
    if _FALSE_INTIMACY.search(hint) or (descriptor.intimacy_risk_hint and "intimacy" in descriptor.intimacy_risk_hint.lower()):
        raise RuntimeContextValidationError(REFUSED_FALSE_INTIMACY, "false intimacy risk refused")
    if not descriptor.uncertainty_displayed:
        return {
            **advisory_only_marker(),
            "status": "review",
            "reason_code": "pres.review.uncertainty_not_displayed",
            "presentation_id": descriptor.presentation_id,
        }
    return {
        **advisory_only_marker(),
        "status": "validated",
        "reason_code": "pres.advisory.descriptor_validated",
        "presentation_id": descriptor.presentation_id,
        "appearance_is_not_truth": True,
    }


__all__ = ["evaluate_descriptor", "validate_descriptor_fixture"]
