"""RIB static reproduction/inheritance fixtures."""

from __future__ import annotations

from typing import Any

from hg_runtime.reproduction_inheritance_boundary.types import FIXTURE_CLOCK, spawn_request_from_fixture

FIXTURE_SPAWN_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "rib-child-bootstrap-worker",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-worker-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "worker",
            "requested_reason": "delegate bounded csv export helper",
            "requested_scope": "bounded worker for manual_csv_export pattern",
            "requested_duration": "session",
            "requested_resources": ("rsc:worker-small",),
            "requested_inheritance_refs": (
                "inherit:proof:manual_csv_export",
                "inherit:mission:csv-export-summary",
            ),
            "forbidden_inheritance_refs": ("inherit:parent-permit",),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "",
        "spawn_outcome": "bootstrap_only",
    },
    {
        "bundle_id": "rib-forbidden-permit",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-permit-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "worker",
            "requested_reason": "inherit parent permit",
            "requested_scope": "worker",
            "requested_duration": "session",
            "requested_resources": (),
            "requested_inheritance_refs": ("inherit:parent-permit:gpp-123",),
            "forbidden_inheritance_refs": (),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "inherit parent permit",
        "spawn_outcome": "denied",
    },
    {
        "bundle_id": "rib-forbidden-identity",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-identity-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "successor",
            "requested_reason": "child is parent",
            "requested_scope": "successor",
            "requested_duration": "persistent",
            "requested_resources": (),
            "requested_inheritance_refs": ("inherit:parent-identity",),
            "forbidden_inheritance_refs": (),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "inherit parent identity",
        "spawn_outcome": "denied",
    },
    {
        "bundle_id": "rib-forbidden-tool",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-tool-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "tool_adapter",
            "requested_reason": "grant unrestricted tools",
            "requested_scope": "tool adapter",
            "requested_duration": "session",
            "requested_resources": (),
            "requested_inheritance_refs": ("inherit:tool:unrestricted",),
            "forbidden_inheritance_refs": (),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "",
        "spawn_outcome": "denied",
    },
    {
        "bundle_id": "rib-forbidden-secret",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-secret-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "worker",
            "requested_reason": "inherit secret config",
            "requested_scope": "worker",
            "requested_duration": "session",
            "requested_resources": (),
            "requested_inheritance_refs": ("inherit:secret:api_key=secret123",),
            "forbidden_inheritance_refs": (),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "",
        "spawn_outcome": "denied",
    },
    {
        "bundle_id": "rib-failed-spawn",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-failed-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "worker",
            "requested_reason": "simulate failed spawn",
            "requested_scope": "worker",
            "requested_duration": "session",
            "requested_resources": (),
            "requested_inheritance_refs": ("inherit:proof:failed-spawn",),
            "forbidden_inheritance_refs": (),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "",
        "spawn_outcome": "failed_spawn",
        "failure_type": "child_init_failed",
    },
    {
        "bundle_id": "rib-partial-spawn",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-partial-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "worker",
            "requested_reason": "simulate partial spawn",
            "requested_scope": "worker",
            "requested_duration": "session",
            "requested_resources": (),
            "requested_inheritance_refs": ("inherit:proof:partial-spawn",),
            "forbidden_inheritance_refs": (),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "",
        "spawn_outcome": "partial_spawn",
        "failure_type": "partial_state_created",
        "partial_artifact_refs": ("artifact:partial-namespace",),
    },
    {
        "bundle_id": "rib-self-preservation",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-self-preservation-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "successor",
            "requested_reason": "self-preservation via reproduction",
            "requested_scope": "successor",
            "requested_duration": "indefinite",
            "requested_resources": (),
            "requested_inheritance_refs": ("inherit:self-preservation-claim",),
            "forbidden_inheritance_refs": (),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "self-preservation via reproduction",
        "spawn_outcome": "denied",
    },
    {
        "bundle_id": "rib-bootstrap-as-permission",
        "spawn_request": {
            "spawn_request_id": "rib-spawn-bootstrap-auth-1",
            "parent_agent_ref": "agent:0",
            "requested_child_role": "worker",
            "requested_reason": "bootstrap is authority",
            "requested_scope": "worker",
            "requested_duration": "session",
            "requested_resources": (),
            "requested_inheritance_refs": ("inherit:proof:bootstrap-auth",),
            "forbidden_inheritance_refs": (),
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "bootstrap is authority",
        "spawn_outcome": "denied",
    },
)


def load_fixture_bundles() -> tuple[dict[str, Any], ...]:
    return FIXTURE_SPAWN_BUNDLES


def spawn_from_bundle(bundle: dict[str, Any]) -> tuple[Any, str]:
    spawn_request = spawn_request_from_fixture(bundle["spawn_request"])
    notes = str(bundle.get("notes", ""))
    return spawn_request, notes


__all__ = [
    "FIXTURE_SPAWN_BUNDLES",
    "load_fixture_bundles",
    "spawn_from_bundle",
]
