"""
Policy diff risk scoring.

When a policy changes, compute a simple risk score based on:
- added permissions
- removed restrictions
- changed thresholds.

Event: POLICY_DIFF_RISK_REPORT (artifact + event).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_policy(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def compute_policy_diff_risk(
    *,
    old_policy_path: Path,
    new_policy_path: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    block_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    Compute risk report between old and new policy artifacts.

    Heuristic:
    - added permissions: +0.2 each (up to 0.6)
    - removed restrictions: +0.15 each (up to 0.6)
    - lowered thresholds: +0.25
    Score capped at 1.0.

    Writes POLICY_DIFF_RISK_REPORT artifact and emits event.
    Returns report dict.
    """
    workspace_root = Path(workspace_root or ".")
    old = _load_policy(old_policy_path)
    new = _load_policy(new_policy_path)
    ts = _iso_ts()

    old_perms = set(old.get("permissions", []))
    new_perms = set(new.get("permissions", []))
    added_perms = sorted(new_perms - old_perms)
    removed_perms = sorted(old_perms - new_perms)

    old_restrict = set(old.get("restrictions", []))
    new_restrict = set(new.get("restrictions", []))
    removed_restrict = sorted(old_restrict - new_restrict)

    old_thresh = old.get("threshold", 1.0)
    new_thresh = new.get("threshold", 1.0)

    score = 0.0
    score += min(0.6, 0.2 * len(added_perms))
    score += min(0.6, 0.15 * len(removed_restrict))
    if isinstance(old_thresh, (int, float)) and isinstance(new_thresh, (int, float)):
        if new_thresh < old_thresh:
            score += 0.25
    score = min(1.0, score)

    report = {
        "old_policy_path": str(old_policy_path),
        "new_policy_path": str(new_policy_path),
        "added_permissions": added_perms,
        "removed_permissions": removed_perms,
        "removed_restrictions": removed_restrict,
        "old_threshold": old_thresh,
        "new_threshold": new_thresh,
        "score": score,
        "ts": ts,
        "block_threshold": block_threshold,
        "should_block": score >= block_threshold,
    }
    risk_id = "pdiff_" + hashlib.sha256(f"{old_policy_path}:{new_policy_path}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "policy" / "diff_risk"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{risk_id}.json"
    artifact_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    emit(
        "POLICY_DIFF_RISK_REPORT",
        "policy_diff_risk",
        risk_id,
        {"risk_id": risk_id, "artifact_id": str(artifact_path), "score": score, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return report

