"""SIL planned RTC event refs — no authority fields."""

from __future__ import annotations

from typing import Any

SIL_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "SIL_SILENCE_RECOMMENDED", "authority_fields": False},
    {"event_type": "SIL_WAIT_RECOMMENDED", "authority_fields": False},
    {"event_type": "SIL_OVEREXPLANATION_DETECTED", "authority_fields": False},
    {"event_type": "SIL_NOISE_SUPPRESSED", "authority_fields": False},
    {"event_type": "SIL_SILENCE_AS_CONSENT_CONTAINED", "authority_fields": False},
    {"event_type": "SIL_REQUIRED_DISCLOSURE_NOT_SUPPRESSED", "authority_fields": False},
    {"event_type": "SIL_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_sil_event_refs() -> tuple[dict[str, Any], ...]:
    return SIL_EVENT_REFS


__all__ = ["SIL_EVENT_REFS", "planned_sil_event_refs"]
