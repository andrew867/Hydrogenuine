"""
Compliance: control checks, attestations, audit export workflow.
ATTESTATION_PUBLISHED, CONTROL_CHECK_RAN, AUDIT_EXPORT_REQUESTED, AUDIT_EXPORT_COMPLETED.
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


def publish_attestation(
    *,
    tenant_id: str,
    environment: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    attestation_content: Dict[str, Any],
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Write attestation artifact, emit ATTESTATION_PUBLISHED. Returns attestation_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    aid = "att_" + hashlib.sha256(f"{tenant_id}:{environment}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "compliance" / "attestations"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{aid}.json"
    path.write_text(json.dumps({"attestation_id": aid, "tenant_id": tenant_id, "environment": environment, "ts": ts, **attestation_content}, indent=2, ensure_ascii=False), encoding="utf-8")
    emit(
        "ATTESTATION_PUBLISHED",
        "attestation",
        aid,
        {"attestation_id": aid, "artifact_id": str(path), "tenant_id": tenant_id, "environment": environment, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return aid


def run_control_check(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    check_name: str,
    result: str,
    summary: Dict[str, Any],
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Write control check summary artifact, emit CONTROL_CHECK_RAN. result: pass | warn | fail. Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    cid = "ctrl_" + hashlib.sha256(f"{check_name}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "compliance" / "controls"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{cid}.json"
    path.write_text(json.dumps({"check_id": cid, "check_name": check_name, "result": result, "ts": ts, **summary}, indent=2, ensure_ascii=False), encoding="utf-8")
    return emit(
        "CONTROL_CHECK_RAN",
        "control_check",
        cid,
        {"check_id": cid, "check_name": check_name, "result": result, "summary_artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def request_audit_export(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    request_id: Optional[str] = None,
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit AUDIT_EXPORT_REQUESTED. Returns request_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    rid = request_id or "audit_req_" + hashlib.sha256(ts.encode()).hexdigest()[:16]
    emit(
        "AUDIT_EXPORT_REQUESTED",
        "audit_export",
        rid,
        {"request_id": rid, "ts": ts, "reason": reason},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return rid


def complete_audit_export(
    *,
    request_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    bundle_artifact_id: str,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit AUDIT_EXPORT_COMPLETED with bundle reference. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "AUDIT_EXPORT_COMPLETED",
        "audit_export",
        request_id,
        {"request_id": request_id, "bundle_artifact_id": bundle_artifact_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def list_attestations(workspace_root: Path, tenant_id: Optional[str] = None, environment: Optional[str] = None) -> List[Dict[str, Any]]:
    """List attestation artifacts under artifacts/compliance/attestations. Optional filter by tenant_id, environment."""
    root = Path(workspace_root) / "artifacts" / "compliance" / "attestations"
    if not root.exists():
        return []
    out = []
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if tenant_id and data.get("tenant_id") != tenant_id:
                continue
            if environment and data.get("environment") != environment:
                continue
            out.append(data)
        except Exception:
            continue
    return out
