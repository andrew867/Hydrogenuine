"""
Retention enforcement worker: expire artifacts by policy, emit ARTIFACT_TOMBSTONED, RETENTION_JOB_RAN.
DATA_REMOVAL_REQUESTED (operator) and DATA_REMOVAL_EXECUTED (after tombstones).
Deterministic: tombstone decisions based on policy + timestamps.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _retention_summary_path(workspace_root: Path, job_id: str) -> Path:
    return Path(workspace_root) / "artifacts" / "retention" / "runs" / f"{job_id}.json"


def record_artifact_tombstoned(
    *,
    artifact_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "retention",
    retention_policy_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit ARTIFACT_TOMBSTONED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"artifact_id": artifact_id, "reason": reason, "ts": ts}
    if retention_policy_id:
        payload["retention_policy_id"] = retention_policy_id
    return emit(
        "ARTIFACT_TOMBSTONED",
        "artifact_tombstone",
        artifact_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def run_retention_job(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    retention_days: int = 365,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    List artifacts under artifacts/, consider expired by retention_days (from mtime or manifest).
    If not dry_run: emit ARTIFACT_TOMBSTONED for each expired; write summary artifact; emit RETENTION_JOB_RAN.
    Returns summary with tombstoned_count, job_id, summary_artifact_path.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    job_id = "ret_" + hashlib.sha256(ts.encode()).hexdigest()[:16]
    root = workspace_root / "artifacts"
    tombstoned: List[str] = []
    if root.exists():
        from hg_core.retention.churn_policy import classify_artifact_path

        cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
        for f in root.rglob("*"):
            if f.is_file():
                try:
                    classification = classify_artifact_path(workspace_root, f)
                    if not classification.auto_tombstone_eligible:
                        continue
                    file_retention_days = classification.retention_days or retention_days
                    file_cutoff = datetime.now(timezone.utc).timestamp() - (file_retention_days * 86400)
                    if f.stat().st_mtime < file_cutoff:
                        rel = str(f.relative_to(workspace_root))
                        aid = hashlib.sha256(rel.encode()).hexdigest()[:16]
                        if not dry_run:
                            record_artifact_tombstoned(
                                artifact_id=aid,
                                scope=scope,
                                actor=actor,
                                reason="retention_expired",
                                retention_policy_id="default",
                                workspace_root=workspace_root,
                            )
                            tombstoned.append(rel)
                except Exception:
                    continue
    summary = {"job_id": job_id, "ts": ts, "tombstoned_count": len(tombstoned), "tombstoned_paths": tombstoned[:100]}
    summary_path = _retention_summary_path(workspace_root, job_id)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if not dry_run:
        emit(
            "RETENTION_JOB_RAN",
            "retention_job",
            job_id,
            {"job_id": job_id, "ts": ts, "tombstoned_count": len(tombstoned), "summary_artifact_path": str(summary_path)},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
    return {"job_id": job_id, "tombstoned_count": len(tombstoned), "summary_artifact_path": str(summary_path)}


def request_data_removal(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    target_refs: List[Dict[str, str]],
    rationale: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit DATA_REMOVAL_REQUESTED (operator/admin). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    req_id = "drq_" + hashlib.sha256(f"{ts}:{target_refs}".encode()).hexdigest()[:16]
    payload = {"request_id": req_id, "target_refs": target_refs, "rationale": rationale, "ts": ts}
    emit(
        "DATA_REMOVAL_REQUESTED",
        "data_removal",
        req_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return req_id  # for use with execute_data_removal


def execute_data_removal(
    *,
    request_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    tombstone_ids: List[str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit DATA_REMOVAL_EXECUTED (links to tombstones). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"request_id": request_id, "tombstone_ids": tombstone_ids, "ts": ts}
    return emit(
        "DATA_REMOVAL_EXECUTED",
        "data_removal",
        request_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
