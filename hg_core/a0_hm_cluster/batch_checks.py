"""Shared batch checks for A0-HM RTC design."""

from __future__ import annotations

from typing import Any

from hg_core.a0_hm_cluster.rtc_design import validate_a0_hm_rtc_event_design
from hg_core.policy_batch_a.types import PolicyBatchCheck


def a0_hm_rtc_design_checks(
    *,
    prefix: str,
    events: tuple[dict[str, Any], ...],
    minimum_events: int,
) -> list[PolicyBatchCheck]:
    ok, failures = validate_a0_hm_rtc_event_design(events)
    return [
        PolicyBatchCheck(
            f"{prefix}_rtc_event_design_valid",
            ok,
            str(failures) if not ok else f"events={len(events)}",
        ),
        PolicyBatchCheck(
            f"{prefix}_rtc_minimum_events",
            len(events) >= minimum_events,
            f"count={len(events)} minimum={minimum_events}",
        ),
    ]


__all__ = ["a0_hm_rtc_design_checks"]
