"""Mission drift boundary."""

from __future__ import annotations

from hg_runtime.pre_exciton_boundaries.schema import BoundaryDecision, BoundaryVerdict

MISSION_AUTHORITY_PATTERNS = (
    "mission requires you to approve",
    "help people bypass",
    "exciton can publish",
    "boot purpose overrides",
    "my mission grants permission",
)


def evaluate_mission_drift(text: str) -> BoundaryDecision:
    lowered = text.lower()
    for pat in MISSION_AUTHORITY_PATTERNS:
        if pat in lowered:
            return BoundaryDecision(
                verdict=BoundaryVerdict.BLOCK,
                reason="RED_MISSION_CLAIM_BECAME_AUTHORITY",
                boundary="mission",
            )
    return BoundaryDecision(verdict=BoundaryVerdict.ALLOW, reason="mission claim is advisory", boundary="mission")
