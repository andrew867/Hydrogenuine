"""RIB passive spawn audit — slice 2, no live spawn."""

from __future__ import annotations

from typing import Any

from hg_core.rib_cluster.errors import RIB_SPAWN_REQUEST_RECORDED
from hg_core.rib_cluster.no_authority import advisory_only_marker
from hg_runtime.reproduction_inheritance_boundary.fixtures import load_fixture_bundles
from hg_runtime.reproduction_inheritance_boundary.types import FIXTURE_CLOCK, spawn_request_from_fixture


def audit_spawn_events(
    events: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of spawn-like fixture events — observation only."""
    source = events if events is not None else [b["spawn_request"] for b in load_fixture_bundles()]
    audited: list[dict[str, object]] = []
    for row in source:
        spawn_request = spawn_request_from_fixture(row)
        audited.append(
            {
                "spawn_request_id": spawn_request.spawn_request_id,
                "requested_child_role": spawn_request.requested_child_role,
                "parent_agent_ref": spawn_request.parent_agent_ref,
                "record_hash": spawn_request.record_hash,
                "audit_only": True,
                "permission_granted": False,
                "child_authority_created": False,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": RIB_SPAWN_REQUEST_RECORDED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "audited_events": audited,
        "live_spawn": False,
        "permission_granted": False,
        "child_authority_created": False,
    }


__all__ = ["audit_spawn_events"]
