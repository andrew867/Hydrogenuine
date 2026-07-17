"""REB cluster batch RTC design checks."""

from __future__ import annotations

from typing import Any

from hg_core.policy_batch_a.types import PolicyBatchCheck
from hg_core.reb_cluster.rtc_design import validate_reb_rtc_event_design


def reb_rtc_design_checks(
    *,
    prefix: str,
    events: tuple[dict[str, Any], ...],
    minimum_events: int,
) -> list[PolicyBatchCheck]:
    valid, failures = validate_reb_rtc_event_design(events)
    return [
        PolicyBatchCheck(
            f"{prefix}_rtc_events_minimum",
            len(events) >= minimum_events,
            f"count={len(events)} minimum={minimum_events}",
        ),
        PolicyBatchCheck(
            f"{prefix}_rtc_events_valid",
            valid,
            ",".join(failures) if failures else "valid",
        ),
    ]


__all__ = ["reb_rtc_design_checks"]
