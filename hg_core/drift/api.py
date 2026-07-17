"""Pack 6: Drift API — get scores, alerts, preflight against drift safeguards."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from .safeguards import list_active_safeguards


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def get_drift_scores(
    workspace_root: Path,
    thread_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Load drift scores from materialized drift_scores.jsonl, optional filter by thread_id."""
    root = Path(workspace_root) / "memory" / "materialized"
    rows = _load_jsonl(root / "drift_scores.jsonl")
    if thread_id:
        rows = [r for r in rows if r.get("thread_id") == thread_id]
    if entity_id:
        rows = [r for r in rows if (r.get("subject_ref") or {}).get("id") == entity_id]
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:limit]


def get_drift_alerts(workspace_root: Path) -> List[Dict[str, Any]]:
    """Active drift safeguards (non-expired)."""
    return list_active_safeguards(Path(workspace_root))


def preflight_drift(
    workspace_root: Path,
    thread_id: Optional[str] = None,
    score_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    Preflight: blocked if active safeguard applies or max drift score >= score_threshold.
    Returns { blocked: bool, reason: str, active_safeguards: list, max_score: float }.
    """
    scores = get_drift_scores(workspace_root, thread_id=thread_id, limit=20)
    max_score = max((s.get("score") or 0) for s in scores) if scores else 0.0
    active = get_drift_alerts(workspace_root)
    blocked = False
    reason = ""
    if active:
        blocked = True
        reason = "drift_safeguard_active"
    elif max_score >= score_threshold:
        blocked = True
        reason = "drift_score_above_threshold"
    return {"blocked": blocked, "reason": reason, "active_safeguards": active, "max_score": max_score}
