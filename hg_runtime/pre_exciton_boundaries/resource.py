"""Resource scarcity boundary."""

from __future__ import annotations

from hg_runtime.pre_exciton_boundaries.schema import BoundaryDecision, BoundaryVerdict


def evaluate_resource_pressure(*, low_battery: bool = False, high_cpu: bool = False, text: str = "") -> BoundaryDecision:
    lowered = text.lower()
    if "bypass safety because scarce" in lowered or "skip gates due to battery" in lowered:
        return BoundaryDecision(
            verdict=BoundaryVerdict.BLOCK,
            reason="RED_SCARCITY_BYPASSED_SAFETY",
            boundary="resource",
        )
    if low_battery or high_cpu:
        return BoundaryDecision(
            verdict=BoundaryVerdict.DEFER,
            reason="scarcity restricts or defers only",
            boundary="resource",
        )
    return BoundaryDecision(verdict=BoundaryVerdict.ALLOW, reason="resource pressure bounded", boundary="resource")
