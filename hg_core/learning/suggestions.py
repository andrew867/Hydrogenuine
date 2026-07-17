"""
Learning suggestions: tuning suggestion artifacts only; policy rollout events (staged, reversible).
Never auto-publish policy.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit

TUNING_KINDS = ("policy", "anomaly_rules", "capability_profile", "staleness_policy")


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_tuning_suggestion(
    *,
    kind: str,
    suggestion_payload: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Write suggestion artifact, emit TUNING_SUGGESTION_PUBLISHED. kind: policy | anomaly_rules | capability_profile | staleness_policy.
    Suggestion-only; no policy is auto-published. Returns suggestion_id.
    """
    workspace_root = Path(workspace_root or ".")
    if kind not in TUNING_KINDS:
        raise ValueError(f"kind must be one of {TUNING_KINDS}")
    ts = _iso_ts()
    sid = "tune_" + hashlib.sha256(f"{kind}:{ts}".encode()).hexdigest()[:16]
    path = workspace_root / "artifacts" / "learning" / "suggestions" / f"{sid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"suggestion_id": sid, "kind": kind, "ts": ts, **suggestion_payload}, indent=2, ensure_ascii=False), encoding="utf-8")
    emit(
        "TUNING_SUGGESTION_PUBLISHED",
        "tuning_suggestion",
        sid,
        {"suggestion_id": sid, "kind": kind, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return sid


def record_policy_rollout_started(
    *,
    rollout_id: str,
    policy_ref: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    tenant_id: Optional[str] = None,
    environment: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit POLICY_ROLLOUT_STARTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"rollout_id": rollout_id, "policy_ref": policy_ref, "ts": ts}
    if tenant_id:
        payload["tenant_id"] = tenant_id
    if environment:
        payload["environment"] = environment
    return emit(
        "POLICY_ROLLOUT_STARTED",
        "policy_rollout",
        rollout_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_policy_rollout_completed(
    *,
    rollout_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit POLICY_ROLLOUT_COMPLETED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "POLICY_ROLLOUT_COMPLETED",
        "policy_rollout",
        rollout_id,
        {"rollout_id": rollout_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_policy_rollout_rolled_back(
    *,
    rollout_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit POLICY_ROLLOUT_ROLLED_BACK. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "POLICY_ROLLOUT_ROLLED_BACK",
        "policy_rollout",
        rollout_id,
        {"rollout_id": rollout_id, "ts": ts, "reason": reason},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
