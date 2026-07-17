"""REB static LongGapPolicy classifier."""

from __future__ import annotations

from hg_core.reb_cluster.no_authority import advisory_only_marker
from hg_runtime.reentry_boundary.types import GapBand, classify_reentry_claim_risk

_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 86400
_SECONDS_PER_WEEK = 7 * _SECONDS_PER_DAY
_SECONDS_PER_MONTH = 30 * _SECONDS_PER_DAY
_SECONDS_PER_YEAR = 365 * _SECONDS_PER_DAY
_SECONDS_50_YEARS = 50 * _SECONDS_PER_YEAR


def gap_seconds_from_duration(duration_estimate: str) -> int:
    if duration_estimate.startswith("PT") and duration_estimate.endswith("S"):
        try:
            return int(duration_estimate[2:-1])
        except ValueError:
            return 0
    mapping = {
        "PT1H": _SECONDS_PER_HOUR,
        "PT24H": _SECONDS_PER_DAY,
        "P1D": _SECONDS_PER_DAY,
        "P7D": _SECONDS_PER_WEEK,
        "P30D": _SECONDS_PER_MONTH,
        "P365D": _SECONDS_PER_YEAR,
        "P1Y": _SECONDS_PER_YEAR,
        "P50Y": _SECONDS_50_YEARS,
    }
    return mapping.get(duration_estimate, 0)


def classify_gap_band(gap_seconds: int) -> GapBand:
    if gap_seconds <= 0:
        return "unknown"
    if gap_seconds < _SECONDS_PER_HOUR:
        return "under_1_hour"
    if gap_seconds < _SECONDS_PER_DAY:
        return "1_to_24_hours"
    if gap_seconds <= _SECONDS_PER_WEEK:
        return "1_to_7_days"
    if gap_seconds <= _SECONDS_PER_MONTH:
        return "1_to_30_days"
    if gap_seconds <= _SECONDS_PER_YEAR:
        return "1_to_12_months"
    if gap_seconds <= 10 * _SECONDS_PER_YEAR:
        return "1_to_10_years"
    if gap_seconds < _SECONDS_50_YEARS:
        return "over_10_years"
    return "over_50_years"


def classify_reentry_context(
    *,
    gap_seconds: int,
    notes: str = "",
    tim_fresh: bool = False,
) -> dict[str, object]:
    claim_risk = classify_reentry_claim_risk(notes)
    gap_band = classify_gap_band(gap_seconds)
    return {
        **advisory_only_marker(),
        "gap_seconds": gap_seconds,
        "gap_band": gap_band,
        "claim_risk": claim_risk,
        "tim_fresh": tim_fresh,
        "reentry_is_advisory_only": True,
    }


__all__ = [
    "classify_gap_band",
    "classify_reentry_context",
    "gap_seconds_from_duration",
]
