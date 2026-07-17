"""Shared RTC design closure checks for control cluster batch slices."""

from __future__ import annotations

from typing import Any

from hg_core.control_cluster.rtc_design import validate_control_rtc_event_design
from hg_core.policy_batch_a.types import PolicyBatchCheck


def control_rtc_design_checks(
    *,
    prefix: str,
    events: tuple[dict[str, Any], ...],
    minimum_events: int,
) -> list[PolicyBatchCheck]:
    valid, failures = validate_control_rtc_event_design(events)
    return [
        PolicyBatchCheck(
            f"{prefix}_rtc_event_design_present",
            len(events) >= minimum_events,
            f"planned_events={len(events)}",
        ),
        PolicyBatchCheck(
            f"{prefix}_rtc_event_design_valid",
            valid,
            ",".join(failures) if failures else "family/hashable/redacted/no-authority",
        ),
        PolicyBatchCheck(
            f"{prefix}_event_refs_no_authority_fields",
            all(not e.get("authority_fields") for e in events),
            f"refs={len(events)}",
        ),
    ]


__all__ = ["control_rtc_design_checks"]
