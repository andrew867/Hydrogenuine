"""
Interop Pack 5: Dispute workflow — open, triage, arbitration, resolve.
DISPUTE_OPENED, DISPUTE_TRIAGED, DISPUTE_REJECTED, DISPUTE_ARBITRATION_STARTED, DISPUTE_RESOLVED.
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


def open_dispute(
    *,
    claimant_domain: str,
    respondent_domain: str,
    subject_ref: Dict[str, Any],
    claim_artifact_id: str,
    evidence_bundle_ids: List[str],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    requested_remedy: Optional[Dict[str, Any]] = None,
    severity: str = "medium",
    bundle_signatures: Optional[Dict[str, str]] = None,
) -> str:
    """Open dispute with claim artifact and evidence bundle refs. Emit DISPUTE_OPENED. Returns dispute_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    dispute_id = "disp_" + hashlib.sha256(f"{claimant_domain}:{respondent_domain}:{ts}".encode()).hexdigest()[:16]
    doc = {
        "dispute_id": dispute_id,
        "claimant_domain": claimant_domain,
        "respondent_domain": respondent_domain,
        "subject_ref": subject_ref,
        "status": "opened",
        "created_ts": ts,
        "claim_artifact_id": claim_artifact_id,
        "evidence_bundle_ids": list(evidence_bundle_ids),
        "requested_remedy": requested_remedy or {},
        "severity": severity,
    }
    if bundle_signatures:
        doc["bundle_signatures"] = bundle_signatures
    root = workspace_root / "artifacts" / "disputes"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{dispute_id}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "DISPUTE_OPENED",
        "dispute",
        dispute_id,
        {"dispute_id": dispute_id, "artifact_id": str(path), "claimant_domain": claimant_domain, "respondent_domain": respondent_domain, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return dispute_id


def load_dispute(workspace_root: Path, dispute_id: str) -> Optional[Dict[str, Any]]:
    """Load dispute by dispute_id. Returns None if not found."""
    path = workspace_root / "artifacts" / "disputes" / f"{dispute_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _update_dispute_status(workspace_root: Path, dispute_id: str, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
    path = workspace_root / "artifacts" / "disputes" / f"{dispute_id}.json"
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["status"] = status
    if extra:
        doc.update(extra)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def triage_dispute(
    *,
    dispute_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    require_evidence_complete: bool = True,
) -> tuple:
    """
    Triage dispute: validate evidence completeness. Emit DISPUTE_TRIAGED or DISPUTE_REJECTED.
    Returns (accepted: bool, event_id: str).
    """
    workspace_root = Path(workspace_root or ".")
    dispute = load_dispute(workspace_root, dispute_id)
    if not dispute:
        return False, ""
    if dispute.get("status") != "opened":
        return False, ""
    ts = _iso_ts()
    if require_evidence_complete:
        bundle_ids = dispute.get("evidence_bundle_ids") or []
        claim_id = dispute.get("claim_artifact_id") or ""
        if not bundle_ids or not claim_id:
            _update_dispute_status(workspace_root, dispute_id, "rejected", {"rejected_ts": ts, "reject_reason": "incomplete_evidence"})
            ev = emit(
                "DISPUTE_REJECTED",
                "dispute",
                dispute_id,
                {"dispute_id": dispute_id, "reason": "incomplete_evidence", "ts": ts},
                scope=scope,
                actor=actor,
                workspace_root=workspace_root,
            )
            return False, ev
    _update_dispute_status(workspace_root, dispute_id, "triage")
    ev = emit(
        "DISPUTE_TRIAGED",
        "dispute",
        dispute_id,
        {"dispute_id": dispute_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return True, ev


def start_arbitration(
    *,
    dispute_id: str,
    arbitrator_ids: List[str],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Assign arbitrators and start arbitration. Emit DISPUTE_ARBITRATION_STARTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    dispute = load_dispute(workspace_root, dispute_id)
    if not dispute or dispute.get("status") not in ("opened", "triage"):
        raise ValueError(f"dispute {dispute_id} not in opened/triage")
    ts = _iso_ts()
    _update_dispute_status(workspace_root, dispute_id, "arbitration", {"arbitrator_ids": arbitrator_ids, "arbitration_started_ts": ts})
    return emit(
        "DISPUTE_ARBITRATION_STARTED",
        "dispute",
        dispute_id,
        {"dispute_id": dispute_id, "arbitrator_ids": arbitrator_ids, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def resolve_dispute(
    *,
    dispute_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Mark dispute resolved (after settlement published). Emit DISPUTE_RESOLVED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    dispute = load_dispute(workspace_root, dispute_id)
    if not dispute:
        raise ValueError(f"dispute not found: {dispute_id}")
    ts = _iso_ts()
    _update_dispute_status(workspace_root, dispute_id, "resolved", {"resolved_ts": ts})
    return emit(
        "DISPUTE_RESOLVED",
        "dispute",
        dispute_id,
        {"dispute_id": dispute_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
