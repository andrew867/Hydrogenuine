"""
Interop Pack 5: Reputation attestation and import — continuity and stake checks.
REPUTATION_ATTESTED, REPUTATION_IMPORTED, REPUTATION_IMPORT_REJECTED.
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


def attest_reputation(
    *,
    subject_did: str,
    domain: str,
    score: float,
    confidence: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    basis_refs: Optional[List[Dict[str, Any]]] = None,
    signature_ref: Optional[str] = None,
) -> str:
    """Publish reputation attestation. Emit REPUTATION_ATTESTED. Returns attestation_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    attestation_id = "rep_" + hashlib.sha256(f"{subject_did}:{domain}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "reputation_attestations"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{attestation_id}.json"
    doc = {
        "attestation_id": attestation_id,
        "subject_did": subject_did,
        "domain": domain,
        "score": score,
        "confidence": confidence,
        "ts": ts,
        "signature": signature_ref or {},
        "basis_refs": basis_refs or [],
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "REPUTATION_ATTESTED",
        "reputation_attestation",
        attestation_id,
        {"attestation_id": attestation_id, "subject_did": subject_did, "domain": domain, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return attestation_id


def import_reputation(
    *,
    attestation_id: str,
    target_domain: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    identity_continuity_artifact_id: Optional[str] = None,
    stake_continuity_artifact_id: Optional[str] = None,
    require_continuity: bool = True,
) -> tuple:
    """
    Import reputation only with continuity and stake linkage when require_continuity.
    Emit REPUTATION_IMPORTED or REPUTATION_IMPORT_REJECTED.
    Returns (accepted: bool, event_id: str).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    path = workspace_root / "artifacts" / "reputation_attestations" / f"{attestation_id}.json"
    if not path.is_file():
        ev = emit(
            "REPUTATION_IMPORT_REJECTED",
            "reputation_attestation",
            attestation_id,
            {"attestation_id": attestation_id, "reason": "attestation_not_found", "ts": ts},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev
    if require_continuity:
        if not identity_continuity_artifact_id or not stake_continuity_artifact_id:
            ev = emit(
                "REPUTATION_IMPORT_REJECTED",
                "reputation_attestation",
                attestation_id,
                {"attestation_id": attestation_id, "reason": "missing_continuity_or_stake_linkage", "ts": ts},
                scope=scope,
                actor=actor,
                workspace_root=workspace_root,
            )
            return False, ev
    root = workspace_root / "artifacts" / "reputation_imports"
    root.mkdir(parents=True, exist_ok=True)
    import_id = "rimp_" + hashlib.sha256(f"{attestation_id}:{target_domain}:{ts}".encode()).hexdigest()[:12]
    import_path = root / f"{import_id}.json"
    doc = {
        "import_id": import_id,
        "attestation_id": attestation_id,
        "target_domain": target_domain,
        "ts": ts,
        "identity_continuity_artifact_id": identity_continuity_artifact_id or "",
        "stake_continuity_artifact_id": stake_continuity_artifact_id or "",
    }
    import_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    ev = emit(
        "REPUTATION_IMPORTED",
        "reputation_attestation",
        import_id,
        {"import_id": import_id, "attestation_id": attestation_id, "target_domain": target_domain, "artifact_id": str(import_path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return True, ev


def load_reputation_attestation(workspace_root: Path, attestation_id: str) -> Optional[Dict[str, Any]]:
    """Load reputation attestation by attestation_id. Returns None if not found."""
    path = workspace_root / "artifacts" / "reputation_attestations" / f"{attestation_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
