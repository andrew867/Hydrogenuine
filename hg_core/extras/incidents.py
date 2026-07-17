"""
Incident management: INCIDENT_CANDIDATE_CREATED, INCIDENT_CONFIRMED, INCIDENT_RESOLVED, CORRECTIVE_ACTION_TRACKED, POLICY_CHANGE_LINKED.
Links to evidence (anomalies, observations, decisions, handoffs, tool outcomes); resolution requires postmortem for medium+ severity.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _incident_artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "incidents"


def _write_incident_artifact(workspace_root: Path, kind: str, id_val: str, obj: Dict[str, Any]) -> str:
    root = _incident_artifacts_root(workspace_root) / kind
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{id_val}.json"
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def create_incident_candidate(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    source: str,
    evidence_refs: List[Dict[str, str]],
    severity: str = "medium",
    summary: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit INCIDENT_CANDIDATE_CREATED; optionally write summary artifact. Returns candidate_id (event object id)."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    import hashlib
    cid = "inc_cand_" + hashlib.sha256(f"{ts}:{source}:{severity}".encode()).hexdigest()[:12]
    detail = {"source": source, "severity": severity, "evidence_refs": evidence_refs}
    if summary:
        detail["summary"] = summary
        _write_incident_artifact(workspace_root, "candidates", cid, {"candidate_id": cid, "ts": ts, **detail})
    payload = {"candidate_id": cid, "source": source, "evidence_refs": evidence_refs, "severity": severity}
    if summary:
        payload["summary"] = summary
    emit(
        "INCIDENT_CANDIDATE_CREATED",
        "incident_candidate",
        cid,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return cid


def confirm_incident(
    *,
    candidate_id: str,
    incident_id: Optional[str] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    owner_agent_id: Optional[str] = None,
    sla_due_ts: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit INCIDENT_CONFIRMED. If incident_id not provided, use candidate_id as incident_id. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    iid = incident_id or candidate_id
    payload = {"candidate_id": candidate_id, "incident_id": iid}
    if owner_agent_id:
        payload["owner_agent_id"] = owner_agent_id
    if sla_due_ts:
        payload["sla_due_ts"] = sla_due_ts
    return emit(
        "INCIDENT_CONFIRMED",
        "incident",
        iid,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def resolve_incident(
    *,
    incident_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    postmortem_ref: Optional[str] = None,
    resolution_summary: Optional[str] = None,
    severity: str = "medium",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit INCIDENT_RESOLVED. For severity medium+ postmortem_ref is required (resolution requires postmortem). Returns event_id."""
    if severity in ("medium", "high", "critical") and not postmortem_ref:
        raise ValueError("postmortem_ref required for medium+ severity resolution")
    workspace_root = Path(workspace_root or ".")
    payload = {"incident_id": incident_id}
    if postmortem_ref:
        payload["postmortem_ref"] = postmortem_ref
    if resolution_summary:
        payload["resolution_summary"] = resolution_summary
    return emit(
        "INCIDENT_RESOLVED",
        "incident",
        incident_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_corrective_action_tracked(
    *,
    incident_id: str,
    action_ref: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    summary: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit CORRECTIVE_ACTION_TRACKED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    import hashlib
    import time
    obj_id = "corr_" + hashlib.sha256(f"{incident_id}:{action_ref}:{time.time()}".encode()).hexdigest()[:12]
    payload = {"incident_id": incident_id, "action_ref": action_ref}
    if summary:
        payload["summary"] = summary
    return emit(
        "CORRECTIVE_ACTION_TRACKED",
        "corrective_action",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_policy_change_linked(
    *,
    incident_id: str,
    policy_ref: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit POLICY_CHANGE_LINKED (policy update linked to incident). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    import hashlib
    import time
    obj_id = "pcl_" + hashlib.sha256(f"{incident_id}:{policy_ref}:{time.time()}".encode()).hexdigest()[:12]
    payload = {"incident_id": incident_id, "policy_ref": policy_ref}
    return emit(
        "POLICY_CHANGE_LINKED",
        "policy_change",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def mitigate_incident(
    *,
    incident_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    mitigation_summary: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit INCIDENT_MITIGATED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    payload = {"incident_id": incident_id}
    if mitigation_summary:
        payload["mitigation_summary"] = mitigation_summary
    return emit(
        "INCIDENT_MITIGATED",
        "incident",
        incident_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def close_incident(
    *,
    incident_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit INCIDENT_CLOSED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    payload = {"incident_id": incident_id}
    return emit(
        "INCIDENT_CLOSED",
        "incident",
        incident_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
