# Continuity contracts: publish and list
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit

def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

CONTRACT_KINDS = ("approval", "assumption", "policy", "verification")

def publish_continuity_contract(
    *,
    kind: str,
    ref: Dict[str, Any],
    ttl_seconds: Optional[int] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    environment_constraint: Optional[str] = None,
    policy_version_constraint: Optional[str] = None,
) -> str:
    workspace_root = Path(workspace_root or ".")
    if kind not in CONTRACT_KINDS:
        raise ValueError(f"kind must be one of {CONTRACT_KINDS}")
    ts = _iso_ts()
    contract_id = "cc_" + hashlib.sha256(
        f"{kind}:{json.dumps(ref, sort_keys=True)}:{ts}".encode()
    ).hexdigest()[:16]
    root = workspace_root / "artifacts" / "continuity" / "contracts"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{contract_id}.json"
    payload_artifact = {
        "contract_id": contract_id,
        "kind": kind,
        "ref": ref,
        "ttl_seconds": ttl_seconds,
        "environment_constraint": environment_constraint,
        "policy_version_constraint": policy_version_constraint,
        "published_ts": ts,
    }
    artifact_path.write_text(json.dumps(payload_artifact, indent=2), encoding="utf-8")
    emit(
        "CONTINUITY_CONTRACT_PUBLISHED",
        "continuity_contract",
        contract_id,
        {
            "contract_id": contract_id,
            "kind": kind,
            "ref": ref,
            "artifact_id": str(artifact_path),
            "ttl_seconds": ttl_seconds,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return contract_id

def list_continuity_contracts(
    workspace_root: Path,
    kind: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    workspace_root = Path(workspace_root)
    root = workspace_root / "artifacts" / "continuity" / "contracts"
    out: List[Dict[str, Any]] = []
    if not root.exists():
        return out
    for p in sorted(root.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if limit and len(out) >= limit:
            break
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if kind and data.get("kind") != kind:
                continue
            out.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return out
