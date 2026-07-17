"""
Continuity checks: evaluate whether approval/assumption/policy/verification is still valid.
Emit CONTINUITY_CHECK_PERFORMED, CONTINUITY_INVALIDATED; create revalidation work item when needed.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hg_core.ledger import emit
from hg_core.continuity.contracts import list_continuity_contracts, CONTRACT_KINDS


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def check_continuity(
    workspace_root: Path,
    kind: str,
    ref: Dict[str, Any],
    *,
    context_environment: Optional[str] = None,
    context_policy_version: Optional[str] = None,
    context_ts: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Evaluate whether the subject (approval/assumption/policy/verification) is still valid
    per published continuity contracts. Returns (valid, reason).
    context_ts: when the subject was created/granted (ISO); if None, use now.
    """
    workspace_root = Path(workspace_root)
    if kind not in CONTRACT_KINDS:
        return False, f"unknown_kind_{kind}"
    contracts = list_continuity_contracts(workspace_root, kind=kind, limit=500)
    # Find matching contract by ref (e.g. same action_id)
    matching = None
    for c in contracts:
        r = c.get("ref") or {}
        if isinstance(r, dict) and ref.items() <= r.items():
            matching = c
            break
        if r == ref:
            matching = c
            break
    if not matching:
        return True, "no_contract"  # no contract => no continuity constraint
    ttl = matching.get("ttl_seconds")
    if ttl is not None and context_ts:
        try:
            # Parse ISO ts (handle Z -> +00:00 for fromisoformat)
            ts_norm = context_ts.replace("Z", "+00:00")
            created = datetime.fromisoformat(ts_norm)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if (now - created).total_seconds() > ttl:
                return False, "ttl_expired"
        except Exception:
            pass
    if context_environment and matching.get("environment_constraint"):
        if context_environment != matching.get("environment_constraint"):
            return False, "environment_mismatch"
    if context_policy_version and matching.get("policy_version_constraint"):
        if context_policy_version != matching.get("policy_version_constraint"):
            return False, "policy_version_mismatch"
    return True, "ok"


def perform_continuity_check(
    *,
    kind: str,
    ref: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    context_environment: Optional[str] = None,
    context_policy_version: Optional[str] = None,
    context_ts: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Run check_continuity and emit CONTINUITY_CHECK_PERFORMED. Returns (valid, event_id).
    """
    workspace_root = Path(workspace_root or ".")
    valid, reason = check_continuity(
        workspace_root,
        kind,
        ref,
        context_environment=context_environment,
        context_policy_version=context_policy_version,
        context_ts=context_ts,
    )
    ts = _iso_ts()
    check_id = "chk_" + hashlib.sha256(f"{kind}:{ts}".encode()).hexdigest()[:16]
    event_id = emit(
        "CONTINUITY_CHECK_PERFORMED",
        "continuity_check",
        check_id,
        {
            "check_id": check_id,
            "kind": kind,
            "ref": ref,
            "valid": valid,
            "reason": reason,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return valid, event_id


def invalidate_continuity(
    *,
    kind: str,
    ref: Dict[str, Any],
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Emit CONTINUITY_INVALIDATED and write rationale artifact. Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    invalid_id = "inv_" + hashlib.sha256(f"{kind}:{reason}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "continuity" / "invalidations"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{invalid_id}.json"
    rationale_path.write_text(
        json.dumps({"invalid_id": invalid_id, "kind": kind, "ref": ref, "reason": reason, "ts": ts}, indent=2),
        encoding="utf-8",
    )
    return emit(
        "CONTINUITY_INVALIDATED",
        "continuity",
        invalid_id,
        {
            "invalid_id": invalid_id,
            "kind": kind,
            "ref": ref,
            "reason": reason,
            "ts": ts,
            "rationale_artifact_id": str(rationale_path),
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def request_revalidation(
    *,
    kind: str,
    ref: Dict[str, Any],
    invalid_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    create_work_item: bool = True,
) -> Tuple[str, Optional[str]]:
    """
    Emit REVALIDATION_REQUESTED. If create_work_item, also create a revalidation work item.
    Returns (event_id, work_item_id or None).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    event_id = emit(
        "REVALIDATION_REQUESTED",
        "continuity",
        invalid_id,
        {
            "invalid_id": invalid_id,
            "kind": kind,
            "ref": ref,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    work_item_id = None
    if create_work_item:
        from hg_core.work_items import create_work_item
        work_item_id = create_work_item(
            wi_type="task",
            title=f"Revalidate {kind}: {ref}",
            scope=scope,
            actor=actor,
            description=f"Continuity invalidated: {invalid_id}. Re-check and re-approve if needed.",
            priority="high",
            workspace_root=workspace_root,
        )
    return event_id, work_item_id
