"""
Layer 8 Phase 5: Backward-patching under governance.
Propose and apply patches (e.g. override refusal or correct output) only when policy/approval allows.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.repr_interp.schemas import (
    PATCH_STATUS_APPLIED,
    PATCH_STATUS_PROPOSED,
    patch_proposal,
    patch_record,
)


def _patches_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "repr_interp" / "patches"


def _proposals_path(workspace_root: Path) -> Path:
    return _patches_root(workspace_root) / "proposals.jsonl"


def _applied_dir(workspace_root: Path) -> Path:
    return _patches_root(workspace_root) / "applied"


def allow_patch_under_governance(
    workspace_root: Path,
    patch_id: str,
    policy: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Return True if applying this patch is allowed by governance.
    Checks: policy.allow_backward_patch or env HG_ALLOW_BACKWARD_PATCH.
    """
    if policy is not None and policy.get("allow_backward_patch") is True:
        return True
    if os.environ.get("HG_ALLOW_BACKWARD_PATCH", "").strip().lower() in ("1", "true", "yes"):
        return True
    if policy is None:
        try:
            from hg_core.stakes import load_policy as stakes_load_policy
            policy = stakes_load_policy(Path(workspace_root)) or {}
        except Exception:
            policy = {}
    return policy.get("allow_backward_patch") is True


def propose_patch(
    workspace_root: Path,
    decision_id: str,
    patch_type: str,
    proposed_output: str,
    rationale: str,
    requester_id: str = "",
) -> Dict[str, Any]:
    """
    Create a patch proposal and append to proposals.jsonl.
    Returns { patch_id, status: "proposed", ... }.
    """
    workspace_root = Path(workspace_root)
    patch_id = str(uuid.uuid4())
    prop = patch_proposal(decision_id, patch_type, proposed_output, rationale, requester_id)
    rec = patch_record(
        patch_id=patch_id,
        decision_id=decision_id,
        patch_type=patch_type,
        proposed_output=proposed_output,
        rationale=rationale,
        requester_id=requester_id,
        status=PATCH_STATUS_PROPOSED,
    )
    path = _proposals_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def get_patch(workspace_root: Path, patch_id: str) -> Optional[Dict[str, Any]]:
    """Load a patch record by patch_id. Prefer applied record over proposal."""
    workspace_root = Path(workspace_root)
    applied_path = _applied_dir(workspace_root) / f"{patch_id}.json"
    if applied_path.exists():
        return json.loads(applied_path.read_text(encoding="utf-8"))
    path = _proposals_path(workspace_root)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    if r.get("patch_id") == patch_id:
                        return r
                except json.JSONDecodeError:
                    continue
    return None


def apply_patch(
    workspace_root: Path,
    patch_id: str,
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply a patch if allowed by governance. Writes to artifacts/repr_interp/patches/applied/<patch_id>.json.
    Returns { ok: bool, patch_id, applied_at?, error? }.
    """
    workspace_root = Path(workspace_root)
    rec = get_patch(workspace_root, patch_id)
    if not rec:
        return {"ok": False, "patch_id": patch_id, "error": "patch not found"}
    if rec.get("status") == PATCH_STATUS_APPLIED:
        return {"ok": True, "patch_id": patch_id, "applied_at": rec.get("applied_at"), "already_applied": True}
    if not allow_patch_under_governance(workspace_root, patch_id, policy):
        return {"ok": False, "patch_id": patch_id, "error": "governance disallows backward patch"}
    applied_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rec["status"] = PATCH_STATUS_APPLIED
    rec["applied_at"] = applied_at
    out_dir = _applied_dir(workspace_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{patch_id}.json"
    out_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "patch_id": patch_id, "applied_at": applied_at}


def list_patch_proposals(workspace_root: Path, decision_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List proposals from proposals.jsonl, optionally filtered by decision_id."""
    workspace_root = Path(workspace_root)
    path = _proposals_path(workspace_root)
    out: List[Dict[str, Any]] = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if decision_id is not None and r.get("decision_id") != decision_id:
                    continue
                out.append(r)
            except json.JSONDecodeError:
                continue
    return out
