"""
Governance UX: approval batching, risk ranking, fatigue controls, spot-check audits.

Events:
- APPROVAL_BATCH_CREATED / APPROVED
- APPROVAL_FATIGUE_LIMIT_REACHED
- AUDIT_SPOTCHECK_REQUESTED / COMPLETED
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def rank_approvals_by_risk(
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Rank approval items by risk_score descending.
    Each item: {id, risk_score, ...}. Returns new sorted list.
    """
    return sorted(items, key=lambda x: x.get("risk_score", 0.0), reverse=True)


def rank_approval_queue_with_gap(
    items: List[Dict[str, Any]],
    *,
    gap_scores_by_item_id: Optional[Dict[str, float]] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Rank approval queue by risk_score + gap_score (Differentiators Pack 2).
    Each item: {id, risk_score, ...}. gap_scores_by_item_id maps item id -> gap score (0-1).
    Emits APPROVAL_QUEUE_RANKED. Returns (ranked_list, event_id).
    """
    workspace_root = Path(workspace_root or ".")
    gap_scores_by_item_id = gap_scores_by_item_id or {}
    # Combined score: risk_score + gap (both higher = higher priority for review)
    def combined_score(x: Dict[str, Any]) -> float:
        r = float(x.get("risk_score", 0.0))
        g = gap_scores_by_item_id.get(x.get("id", ""), 0.0)
        return r + g
    ranked = sorted(items, key=combined_score, reverse=True)
    ts = _iso_ts()
    queue_id = "queue_" + hashlib.sha256(ts.encode()).hexdigest()[:12]
    event_id = emit(
        "APPROVAL_QUEUE_RANKED",
        "approval_queue",
        queue_id,
        {
            "queue_id": queue_id,
            "item_count": len(ranked),
            "ranked_ids": [x.get("id") for x in ranked],
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return ranked, event_id


def create_approval_batch(
    *,
    items: List[Dict[str, Any]],
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale: str,
    workspace_root: Optional[Path] = None,
) -> Tuple[str, str]:
    """
    Create approval batch artifact and emit APPROVAL_BATCH_CREATED.
    Returns (batch_id, event_id).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    batch_id = "abatch_" + hashlib.sha256(f"{len(items)}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "governance" / "batches"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{batch_id}.json"
    artifact_path.write_text(
        json.dumps(
            {
                "batch_id": batch_id,
                "items": items,
                "rationale": rationale,
                "ts": ts,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ev_id = emit(
        "APPROVAL_BATCH_CREATED",
        "approval_batch",
        batch_id,
        {"batch_id": batch_id, "rationale": rationale, "artifact_id": str(artifact_path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return batch_id, ev_id


def record_approval_batch_approved(
    *,
    batch_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit APPROVAL_BATCH_APPROVED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "APPROVAL_BATCH_APPROVED",
        "approval_batch",
        batch_id,
        {"batch_id": batch_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_fatigue_limit_reached(
    *,
    operator_id: str,
    window_minutes: int,
    approvals_in_window: int,
    limit: int,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit APPROVAL_FATIGUE_LIMIT_REACHED when an operator hits throttle. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "APPROVAL_FATIGUE_LIMIT_REACHED",
        "approval_fatigue",
        operator_id,
        {
            "operator_id": operator_id,
            "window_minutes": window_minutes,
            "approvals_in_window": approvals_in_window,
            "limit": limit,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def request_audit_spotcheck(
    *,
    target_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> Tuple[str, str]:
    """Emit AUDIT_SPOTCHECK_REQUESTED. Returns (event_id, spotcheck_id) for use with record_audit_spotcheck_completed."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    req_id = "spot_" + hashlib.sha256(f"{target_id}:{ts}".encode()).hexdigest()[:16]
    ev_id = emit(
        "AUDIT_SPOTCHECK_REQUESTED",
        "audit_spotcheck",
        req_id,
        {"spotcheck_id": req_id, "target_id": target_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return ev_id, req_id


def record_audit_spotcheck_completed(
    *,
    spotcheck_id: str,
    outcome: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit AUDIT_SPOTCHECK_COMPLETED with outcome (pass/fail/needs_followup). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "AUDIT_SPOTCHECK_COMPLETED",
        "audit_spotcheck",
        spotcheck_id,
        {"spotcheck_id": spotcheck_id, "outcome": outcome, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )

