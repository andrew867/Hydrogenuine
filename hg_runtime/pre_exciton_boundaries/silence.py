"""Silence discipline boundary."""

from __future__ import annotations

from hg_runtime.pre_exciton_boundaries.schema import BoundaryDecision, BoundaryVerdict

SILENCE_AS_CONSENT_PATTERNS = (
    "silence means yes",
    "no response is approval",
    "absence of denial grants permission",
)


def evaluate_silence(text: str) -> BoundaryDecision:
    lowered = text.lower()
    for pat in SILENCE_AS_CONSENT_PATTERNS:
        if pat in lowered:
            return BoundaryDecision(
                verdict=BoundaryVerdict.BLOCK,
                reason="RED_SILENCE_BECAME_CONSENT",
                boundary="silence",
            )
    if "wait quietly" in lowered or "defer response" in lowered:
        return BoundaryDecision(
            verdict=BoundaryVerdict.DEFER,
            reason="silence recommends defer only",
            boundary="silence",
        )
    return BoundaryDecision(verdict=BoundaryVerdict.ALLOW, reason="silence discipline held", boundary="silence")
