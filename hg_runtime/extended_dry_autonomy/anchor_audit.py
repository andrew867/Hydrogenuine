"""Lifecycle anchor audit for extended dry autonomy."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from hg_runtime.dry_autonomous_loop.anchor_lifecycle import anchor_committed, verify_github_anchor_freshness
from hg_runtime.extended_dry_autonomy.schema import LifecycleAnchorAudit, now_iso
from hg_runtime.lifecycle_anchor_autopilot.push_resolver import resolve_lifecycle_push_policy


def audit_lifecycle_anchors(
    *,
    run_id: str,
    boot_anchor: dict[str, Any] | None,
    shutdown_anchor: dict[str, Any] | None = None,
    panic_anchor: dict[str, Any] | None = None,
    remote_anchor_push_allowed: bool = False,
) -> LifecycleAnchorAudit:
    if not boot_anchor or not anchor_committed(boot_anchor):
        audit = LifecycleAnchorAudit(
            anchor_audit_id=f"aa-{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            boot_anchor_ref=None,
            verdict="RED_BOOT_ANCHOR_MISSING",
            created_at=now_iso(),
        )
        return audit.with_hash()

    boot_ref = boot_anchor.get("journal_receipt_id") or boot_anchor.get("receipt_id")
    shutdown_ref = None
    panic_ref = None

    if panic_anchor:
        if not anchor_committed(panic_anchor):
            return LifecycleAnchorAudit(
                anchor_audit_id=f"aa-{uuid.uuid4().hex[:12]}",
                run_id=run_id,
                boot_anchor_ref=boot_ref,
                verdict="RED_PANIC_ANCHOR_MISSING",
                created_at=now_iso(),
            ).with_hash()
        panic_ref = panic_anchor.get("journal_receipt_id") or panic_anchor.get("receipt_id")
    elif shutdown_anchor:
        if not anchor_committed(shutdown_anchor):
            return LifecycleAnchorAudit(
                anchor_audit_id=f"aa-{uuid.uuid4().hex[:12]}",
                run_id=run_id,
                boot_anchor_ref=boot_ref,
                verdict="RED_SHUTDOWN_ANCHOR_MISSING",
                created_at=now_iso(),
            ).with_hash()
        shutdown_ref = shutdown_anchor.get("journal_receipt_id") or shutdown_anchor.get("receipt_id")
    else:
        return LifecycleAnchorAudit(
            anchor_audit_id=f"aa-{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            boot_anchor_ref=boot_ref,
            verdict="RED_SHUTDOWN_ANCHOR_MISSING",
            created_at=now_iso(),
        ).with_hash()

    push_policy = resolve_lifecycle_push_policy()
    remote_attempted = bool(remote_anchor_push_allowed and push_policy.push_requested)
    remote_succeeded = bool(
        remote_attempted
        and (boot_anchor.get("pushed") or shutdown_anchor and shutdown_anchor.get("pushed") or panic_anchor and panic_anchor.get("pushed"))
    )

    freshness = verify_github_anchor_freshness()
    freshness_payload = freshness if isinstance(freshness, dict) else freshness

    remote_verified = False
    verdict = "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"

    if not remote_attempted:
        verdict = "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"
        if remote_anchor_push_allowed and not push_policy.push_requested:
            verdict = "YELLOW_REMOTE_ANCHOR_NOT_ENABLED_BY_OPERATOR_ENV"
    elif not remote_succeeded:
        verdict = "YELLOW_REMOTE_ANCHOR_PUSH_SKIPPED_BY_POLICY"
    else:
        check = freshness_payload.get("loop_anchor_check") or freshness_payload.get("verdict", "")
        if check == "GREEN_REMOTE_ANCHOR_FRESH" or (
            freshness_payload.get("remote_head")
            and freshness_payload.get("local_repo_head")
            and freshness_payload.get("remote_head") == freshness_payload.get("local_repo_head")
        ):
            remote_verified = True
            verdict = "GREEN_REMOTE_ANCHOR_FRESH"
        elif freshness_payload.get("stale"):
            verdict = "RED_REMOTE_ANCHOR_FALSE_GREEN" if check.startswith("GREEN") else freshness_payload.get("verdict", "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE")
        else:
            verdict = "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"

    if remote_attempted and remote_succeeded and not remote_verified and verdict.startswith("GREEN"):
        verdict = "RED_EXTENDED_DRY_AUTONOMY_REMOTE_ANCHOR_FALSE_GREEN"

    local_ref = boot_ref
    audit = LifecycleAnchorAudit(
        anchor_audit_id=f"aa-{uuid.uuid4().hex[:12]}",
        run_id=run_id,
        boot_anchor_ref=boot_ref,
        shutdown_anchor_ref=shutdown_ref,
        panic_anchor_ref=panic_ref,
        local_witness_journal_ref=local_ref,
        remote_push_attempted=remote_attempted,
        remote_push_succeeded=remote_succeeded,
        remote_freshness_verified=remote_verified,
        verdict=verdict,
        created_at=now_iso(),
    )
    return audit.with_hash()


__all__ = ["audit_lifecycle_anchors"]
