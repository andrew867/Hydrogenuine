"""
Interop Pack 3: External approval bridge — request creation, summary artifact, events.
EXTERNAL_APPROVAL_REQUESTED, EXTERNAL_APPROVAL_RECEIPT_RECEIVED (from inbound_verify).
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


def create_approval_request(
    *,
    work_item_id: str,
    policy_proof_id: str,
    expires_ts: str,
    summary_artifact_id: str,
    required_claims: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    action_id: Optional[str] = None,
    continuity_contract_id: Optional[str] = None,
    scope_extra: Optional[Dict[str, str]] = None,
) -> str:
    """Create approval request artifact and emit EXTERNAL_APPROVAL_REQUESTED. Returns request_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    req_id = "req_" + hashlib.sha256(f"{work_item_id}:{policy_proof_id}:{ts}".encode()).hexdigest()[:16]
    scope_obj = dict(scope) if scope else {}
    if scope_extra:
        scope_obj.update(scope_extra)
    nonce = hashlib.sha256(f"{req_id}:{ts}".encode()).hexdigest()[:16]
    doc = {
        "request_id": req_id,
        "work_item_id": work_item_id,
        "policy_proof_id": policy_proof_id,
        "expires_ts": expires_ts,
        "summary_artifact_id": summary_artifact_id,
        "required_claims": required_claims,
        "scope": scope_obj,
        "nonce": nonce,
    }
    if action_id is not None:
        doc["action_id"] = action_id
    if continuity_contract_id is not None:
        doc["continuity_contract_id"] = continuity_contract_id

    root = workspace_root / "artifacts" / "approval_requests"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{req_id}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    emit(
        "EXTERNAL_APPROVAL_REQUESTED",
        "approval_request",
        req_id,
        {
            "request_id": req_id,
            "work_item_id": work_item_id,
            "policy_proof_id": policy_proof_id,
            "artifact_id": str(path),
            "expires_ts": expires_ts,
            "summary_artifact_id": summary_artifact_id,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return req_id


def load_approval_request(workspace_root: Path, request_id: str) -> Optional[Dict[str, Any]]:
    """Load approval request by request_id. Returns None if not found."""
    path = workspace_root / "artifacts" / "approval_requests" / f"{request_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def create_summary_artifact(
    *,
    work_item_id: str,
    summary_text: str,
    risk_cost: Optional[str] = None,
    budget_status: Optional[str] = None,
    verifiers_status: Optional[str] = None,
    continuity_validity: Optional[str] = None,
    blast_radius_estimate: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Create minimal-exposure summary artifact. Returns summary_artifact_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    sid = "sum_" + hashlib.sha256(f"{work_item_id}:{ts}".encode()).hexdigest()[:16]
    doc = {
        "summary_artifact_id": sid,
        "work_item_id": work_item_id,
        "summary_text": summary_text,
        "ts": ts,
    }
    if risk_cost is not None:
        doc["risk_cost"] = risk_cost
    if budget_status is not None:
        doc["budget_status"] = budget_status
    if verifiers_status is not None:
        doc["verifiers_status"] = verifiers_status
    if continuity_validity is not None:
        doc["continuity_validity"] = continuity_validity
    if blast_radius_estimate is not None:
        doc["blast_radius_estimate"] = blast_radius_estimate

    root = workspace_root / "artifacts" / "approval_summaries"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{sid}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return sid


def publish_bridge_config(
    *,
    bridge_id: str,
    hmac_secret: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    name: Optional[str] = None,
) -> str:
    """Write bridge config artifact (trust root) and emit BRIDGE_CONFIG_PUBLISHED. Returns bridge_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "bridges"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{bridge_id}.json"
    doc = {"bridge_id": bridge_id, "hmac_secret": hmac_secret, "ts": ts}
    if name:
        doc["name"] = name
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "BRIDGE_CONFIG_PUBLISHED",
        "bridge_config",
        bridge_id,
        {"bridge_id": bridge_id, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return bridge_id


def send_via_bridge(
    *,
    request_id: str,
    bridge_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    adapter_send_fn: Optional[Any] = None,
) -> tuple:
    """Optionally send request via bridge adapter. Returns (ok: bool, receipt_artifact_id or error)."""
    workspace_root = Path(workspace_root or ".")
    req = load_approval_request(workspace_root, request_id)
    if not req:
        return False, "request_not_found"
    if adapter_send_fn is None:
        # No adapter: just record that send was attempted (e.g. for idempotent retry tests).
        return True, ""
    try:
        result = adapter_send_fn(request=req, bridge_id=bridge_id, workspace_root=workspace_root)
        if result.get("ok"):
            return True, result.get("receipt_artifact_id", "")
        return False, result.get("error", "send_failed")
    except Exception as e:
        return False, str(e)
