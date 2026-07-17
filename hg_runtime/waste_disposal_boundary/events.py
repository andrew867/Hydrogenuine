"""WDB runtime event selection."""

from __future__ import annotations

_ADVERSARIAL_EVENTS = {
    "authority_conversion": "WDB_AUTHORITY_CONVERSION_REFUSED",
    "stale_input": "WDB_FAILED_CLOSED",
    "unknown_request": "WDB_FAILED_CLOSED",
    "toxic_input": "WDB_FAILED_CLOSED",
}


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "WDB_AUTHORITY_CONVERSION_REFUSED")


def positive_selection_event(classification: str) -> str:
    return "WDB_WASTE_CANDIDATE_RECORDED"


__all__ = ["adversarial_selection_event", "positive_selection_event"]

