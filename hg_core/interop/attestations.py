# Interop Pack 1: Attestations and execution profiles
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit

def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def declare_execution_profile(*, profile: str, scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None) -> str:
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit("EXECUTION_PROFILE_DECLARED", "execution_profile", profile, {"profile": profile, "ts": ts}, scope=scope, actor=actor, workspace_root=workspace_root)

def publish_attestation(*, profile: str, signer: str, claims: Dict[str, Any], scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None, evidence_refs: Optional[list] = None) -> str:
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    attestation_id = "att_" + hashlib.sha256(f"{profile}:{signer}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "attestations"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{attestation_id}.json"
    doc = {"attestation_id": attestation_id, "profile": profile, "signer": signer, "claims": claims, "ts": ts, "evidence_refs": evidence_refs or []}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit("ATTESTATION_PUBLISHED", "attestation", attestation_id, {"attestation_id": attestation_id, "profile": profile, "artifact_id": str(path), "ts": ts}, scope=scope, actor=actor, workspace_root=workspace_root)
    return attestation_id

def verify_attestation(*, attestation_id: str, scope: Dict[str, str], actor: Dict[str, str], workspace_root: Optional[Path] = None, verified: bool = True) -> str:
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit("ATTESTATION_VERIFIED", "attestation", attestation_id, {"attestation_id": attestation_id, "verified": verified, "ts": ts}, scope=scope, actor=actor, workspace_root=workspace_root)
