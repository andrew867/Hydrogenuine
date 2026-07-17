from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from hg_core.ledger import emit

def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def make_receipt(req: Dict[str, Any], resp: Dict[str, Any], status: str = "ok") -> Dict[str, Any]:
    ts = _iso_ts()
    req_hash = hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()[:32]
    resp_hash = hashlib.sha256(json.dumps(resp, sort_keys=True).encode()).hexdigest()[:32]
    return {"request": req, "response": resp, "status": status, "request_hash": req_hash, "response_hash": resp_hash, "ts": ts}

def register_connector(*, connector_id: str, name: str, scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None) -> str:
    w = Path(workspace_root or ".")
    ts = _iso_ts()
    root = w / "artifacts" / "connectors"
    root.mkdir(parents=True, exist_ok=True)
    path = root / (connector_id + ".json")
    path.write_text(json.dumps({"connector_id": connector_id, "name": name, "registered_ts": ts}, indent=2), encoding="utf-8")
    return emit("CONNECTOR_REGISTERED", "connector", connector_id, {"connector_id": connector_id, "artifact_id": str(path), "ts": ts}, scope=scope, actor=actor, workspace_root=w)

def request_connector_call(*, connector_id: str, operation: str, work_item_id: str, scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None) -> str:
    """Emit CONNECTOR_REQUESTED. Returns call_id for use with execute_connector_call/deny_connector_call."""
    w = Path(workspace_root or ".")
    ts = _iso_ts()
    call_id = "call_" + hashlib.sha256((connector_id + ":" + operation + ":" + ts).encode()).hexdigest()[:16]
    emit("CONNECTOR_REQUESTED", "connector_call", call_id, {"call_id": call_id, "connector_id": connector_id, "operation": operation, "work_item_id": work_item_id, "ts": ts}, scope=scope, actor=actor, workspace_root=w)
    return call_id

def execute_connector_call(*, call_id: str, receipt_artifact_id: str, scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None) -> str:
    w = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit("CONNECTOR_CALL_EXECUTED", "connector_call", call_id, {"call_id": call_id, "receipt_artifact_id": receipt_artifact_id, "ts": ts}, scope=scope, actor=actor, workspace_root=w)

def deny_connector_call(*, call_id: str, policy_proof_id: str, reason: str, scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None) -> str:
    w = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit("CONNECTOR_CALL_DENIED", "connector_call", call_id, {"call_id": call_id, "policy_proof_id": policy_proof_id, "reason": reason, "ts": ts}, scope=scope, actor=actor, workspace_root=w)


def verify_connector_call(*, call_id: str, verified: bool, scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None) -> str:
    """Emit CONNECTOR_CALL_VERIFIED (optional post-execution verification). Returns event_id."""
    w = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit("CONNECTOR_CALL_VERIFIED", "connector_call", call_id, {"call_id": call_id, "verified": verified, "ts": ts}, scope=scope, actor=actor, workspace_root=w)
