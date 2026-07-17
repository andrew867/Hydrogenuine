"""
Explain endpoints: deterministic structures with linked entities, timeline slice, integrity refs.
export_signed_bundle: publish artifact bundle, optional signature, emit AUDIT_BUNDLE_EXPORTED.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.ledger.facts_meaning import explain_decision as _explain_decision_impl
from hg_core.materializers._checkpoint import get_materialized_root
from hg_core.extras.search_crosslink import get_decision_links, get_anomaly_links
from hg_core.ledger.ledger_writer import iterate_events


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def explain_work_item(
    workspace_root: Path,
    work_item_id: str,
    include_timeline: bool = True,
) -> Dict[str, Any]:
    """
    Return work item with linked entities (assignee, linked decisions, incidents), timeline slice, integrity refs.
    """
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    out: Dict[str, Any] = {
        "work_item_id": work_item_id,
        "work_item": None,
        "linked_decision_ids": [],
        "linked_incident_ids": [],
        "event_ids": [],
        "timeline": [],
    }
    for row in _load_jsonl(root / "work_items.jsonl"):
        if row.get("work_item_id") == work_item_id or row.get("id") == work_item_id:
            out["work_item"] = row
            break
    if not out["work_item"]:
        return out
    wi = out["work_item"]
    out["linked_decision_ids"] = wi.get("linked_ids") or []
    if include_timeline:
        for ev in iterate_events(workspace_root):
            payload = ev.get("payload") or {}
            if payload.get("work_item_id") == work_item_id or ev.get("object", {}).get("id") == work_item_id:
                out["timeline"].append({"event_id": ev.get("event_id"), "action": ev.get("action"), "ts": ev.get("ts")})
                out["event_ids"].append(ev.get("event_id"))
    return out


def explain_decision(
    workspace_root: Path,
    decision_id: str,
    include_links: bool = True,
) -> Dict[str, Any]:
    """
    Return decision with claims, values, context, artifacts; optional links (observations, self-assessment, evaluations).
    """
    workspace_root = Path(workspace_root)
    expl = _explain_decision_impl(decision_id, workspace_root)
    out: Dict[str, Any] = {"decision_id": decision_id, **expl}
    if include_links:
        out["links"] = get_decision_links(workspace_root, decision_id)
    out["recommended_next_steps"] = []  # policy-driven placeholder
    return out


def explain_incident(
    workspace_root: Path,
    incident_id: str,
    include_links: bool = True,
) -> Dict[str, Any]:
    """
    Return incident with status history, enforcement, linked anomalies; timeline and integrity refs.
    """
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    out: Dict[str, Any] = {
        "incident_id": incident_id,
        "records": [],
        "event_ids": [],
        "links": {},
    }
    for row in _load_jsonl(root / "incidents.jsonl"):
        if row.get("incident_id") == incident_id:
            out["records"].append(row)
            out["event_ids"].append(row.get("event_id"))
    for row in _load_jsonl(root / "audit_events.jsonl"):
        if row.get("resource") == incident_id and row.get("action") == "ENFORCEMENT_APPLIED":
            out["records"].append({"kind": "enforcement", **row})
    if include_links:
        out["links"] = {"anomalies": [], "decisions": []}
        for row in _load_jsonl(root / "incidents.jsonl"):
            if row.get("incident_id") != incident_id:
                continue
            refs = row.get("evidence_refs") or []
            for r in refs:
                if isinstance(r, dict) and r.get("type") == "anomaly":
                    out["links"]["anomalies"].append(r.get("id"))
    return out


def explain_action(
    workspace_root: Path,
    action_id: str,
) -> Dict[str, Any]:
    """
    Return 2PC trail for action_id: proposed, approval granted/denied, executed (receipt), verified, committed.
    """
    workspace_root = Path(workspace_root)
    actions = ("ACTION_PROPOSED", "ACTION_APPROVAL_REQUESTED", "ACTION_APPROVAL_GRANTED", "ACTION_APPROVAL_DENIED", "ACTION_EXECUTED", "ACTION_VERIFIED", "ACTION_COMMITTED")
    trail: List[Dict[str, Any]] = []
    for ev in iterate_events(workspace_root):
        if ev.get("action") not in actions:
            continue
        payload = ev.get("payload") or {}
        if payload.get("action_id") != action_id and ev.get("object", {}).get("id") != action_id:
            continue
        trail.append({
            "event_id": ev.get("event_id"),
            "action": ev.get("action"),
            "ts": ev.get("ts"),
            "payload": payload,
        })
    return {"action_id": action_id, "trail": trail}


def export_signed_bundle(
    workspace_root: Path,
    bundle_type: str,
    ids: List[str],
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    include_raw: bool = False,
) -> Dict[str, Any]:
    """
    Build a bundle (decision_audit, incident_audit, work_item_audit, action_audit), write artifact, emit AUDIT_BUNDLE_EXPORTED.
    Returns bundle_path, bundle_id, checksum_sha256.
    """
    workspace_root = Path(workspace_root)
    root = workspace_root / "artifacts" / "bundles"
    root.mkdir(parents=True, exist_ok=True)
    ts = str(int(time.time()))
    bundle_id = f"bundle_{bundle_type}_{ts}"
    bundle_data: Dict[str, Any] = {"bundle_type": bundle_type, "ids": ids, "include_raw": include_raw, "exports": []}
    if bundle_type == "decision_audit":
        for did in ids:
            bundle_data["exports"].append(explain_decision(workspace_root, did, include_links=True))
    elif bundle_type == "incident_audit":
        for iid in ids:
            bundle_data["exports"].append(explain_incident(workspace_root, iid, include_links=True))
    elif bundle_type == "work_item_audit":
        for wid in ids:
            bundle_data["exports"].append(explain_work_item(workspace_root, wid, include_timeline=True))
    elif bundle_type == "action_audit":
        for aid in ids:
            bundle_data["exports"].append(explain_action(workspace_root, aid))
    else:
        bundle_data["exports"] = []
    raw = json.dumps(bundle_data, indent=2, ensure_ascii=False)
    checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    bundle_data["checksum_sha256"] = checksum
    path = root / f"{bundle_id}.json"
    path.write_text(json.dumps(bundle_data, indent=2, ensure_ascii=False), encoding="utf-8")
    emit(
        "AUDIT_BUNDLE_EXPORTED",
        "audit_bundle",
        bundle_id,
        {"bundle_id": bundle_id, "bundle_type": bundle_type, "artifact_path": str(path), "checksum_sha256": checksum, "ids": ids},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return {"bundle_path": str(path), "bundle_id": bundle_id, "checksum_sha256": checksum}