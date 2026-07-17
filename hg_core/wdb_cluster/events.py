"""WDB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.wdb_cluster.rtc_design import wdb_rtc_event

WDB_EVENT_REFS: tuple[dict[str, Any], ...] = (
        wdb_rtc_event("WDB_WASTE_CANDIDATE_RECORDED"),
wdb_rtc_event("WDB_EXPIRY_SIGNAL_RECORDED"),
wdb_rtc_event("WDB_DISPOSAL_PROPOSAL_CREATED"),
wdb_rtc_event("WDB_TOMBSTONE_PROPOSAL_CREATED"),
wdb_rtc_event("WDB_PRUNE_PROPOSAL_CREATED"),
wdb_rtc_event("WDB_RETENTION_PROTECTED_REFUSED"),
wdb_rtc_event("WDB_PROOF_DELETION_REFUSED"),
wdb_rtc_event("WDB_AUTHORITY_CONVERSION_REFUSED"),
wdb_rtc_event("WDB_FAILED_CLOSED"),
)


def planned_wdb_event_refs() -> tuple[dict[str, Any], ...]:
    return WDB_EVENT_REFS


__all__ = ["WDB_EVENT_REFS", "planned_wdb_event_refs"]

