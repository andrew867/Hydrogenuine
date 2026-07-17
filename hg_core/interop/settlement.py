"""
Interop Pack 5: Settlement — publish only with quorum proof.
SETTLEMENT_PUBLISHED.
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


def publish_settlement(
    *,
    dispute_id: str,
    outcome: str,
    quorum_proof_artifact_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    actions_taken: Optional[List[Dict[str, Any]]] = None,
    expires_ts: Optional[str] = None,
) -> str:
    """Publish settlement only when quorum proof is provided. outcome: accept | reject | partial. Returns settlement_id."""
    if outcome not in ("accept", "reject", "partial"):
        raise ValueError("outcome must be accept, reject, or partial")
    if not quorum_proof_artifact_id:
        raise ValueError("quorum_proof_artifact_id required")
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    settlement_id = "settle_" + hashlib.sha256(f"{dispute_id}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "settlements"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{settlement_id}.json"
    doc = {
        "settlement_id": settlement_id,
        "dispute_id": dispute_id,
        "outcome": outcome,
        "published_ts": ts,
        "artifact_id": str(path),
        "quorum_proof_artifact_id": quorum_proof_artifact_id,
        "actions_taken": actions_taken or [],
    }
    if expires_ts:
        doc["expires_ts"] = expires_ts
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "SETTLEMENT_PUBLISHED",
        "settlement",
        settlement_id,
        {"settlement_id": settlement_id, "dispute_id": dispute_id, "outcome": outcome, "artifact_id": str(path), "quorum_proof_artifact_id": quorum_proof_artifact_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return settlement_id


def load_settlement(workspace_root: Path, settlement_id: str) -> Optional[Dict[str, Any]]:
    """Load settlement by settlement_id. Returns None if not found."""
    path = workspace_root / "artifacts" / "settlements" / f"{settlement_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
