"""RIB runtime planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.rib_cluster.events import planned_rib_event_refs


def lifecycle_selection_event(lifecycle_state: str, *, failure_type: str | None = None) -> str | None:
    mapping = {
        "denied": "RIB_CHILD_SPAWN_DENIED",
        "bootstrap_created": "RIB_CHILD_BOOTSTRAP_PACKET_CREATED",
        "spawn_attempted": "RIB_CHILD_SPAWN_ATTEMPTED",
        "spawned": "RIB_CHILD_SPAWNED",
        "partial_spawn": "RIB_CHILD_PARTIAL_SPAWN_RECORDED",
        "failed_spawn": "RIB_CHILD_FAILED_SPAWN_RECORDED",
        "rolled_back": "RIB_CHILD_ROLLBACK_COMPLETED",
    }
    if lifecycle_state in mapping:
        return mapping[lifecycle_state]
    if failure_type == "partial_state_created":
        return "RIB_CHILD_PARTIAL_SPAWN_RECORDED"
    return None


def inheritance_selection_event(decision: str, inheritance_type: str) -> str | None:
    if decision == "forbidden":
        if inheritance_type == "identity_ref":
            return "RIB_INHERITED_IDENTITY_REFUSED"
        if inheritance_type == "permit_ref":
            return "RIB_INHERITED_PERMISSION_REFUSED"
        return "RIB_AUTHORITY_CONVERSION_CONTAINED"
    if decision in {"allow_ref_only", "allow_summary", "require_operator_review"}:
        return "RIB_INHERITANCE_DECISION_RECORDED"
    if decision == "unknown_fail_closed":
        return "RIB_SIGNAL_REFUSED"
    return None


__all__ = [
    "inheritance_selection_event",
    "lifecycle_selection_event",
    "planned_rib_event_refs",
]
