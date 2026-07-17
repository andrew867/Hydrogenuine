"""
Safe search over materialized data (ids + safe text: titles, summaries, rationale, tags).
Cross-link APIs: decision -> claims, observations, self-assessment, evaluations, incidents; anomaly -> observation, incidents, modulations.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger.ledger_writer import iterate_events


def _safe_text(row: Dict[str, Any], keys: List[str]) -> str:
    parts = []
    for k in keys:
        v = row.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, (list, dict)):
            parts.append(json.dumps(v, ensure_ascii=False)[:500])
    return " ".join(parts)


def build_search_index(workspace_root: Path) -> List[Dict[str, Any]]:
    """Build a flat search index from materialized tables: id-like fields + safe text (title, summary, rationale, tags). Returns list of index entries."""
    index: List[Dict[str, Any]] = []
    safe_text_keys = ("title", "summary", "rationale", "notes", "tags", "resolution_summary", "source")
    for ev in iterate_events(Path(workspace_root)):
        if ev.get("action") != "DECISION_COMMITTED":
            continue
        payload = ev.get("payload") or {}
        decision_id = payload.get("decision_id") or (ev.get("object") or {}).get("id") or ev.get("event_id") or ""
        if not decision_id:
            continue
        row = {
            "decision_id": decision_id,
            "title": payload.get("title", ""),
            "summary": payload.get("summary", ""),
            "rationale": payload.get("rationale", ""),
            "notes": payload.get("notes", ""),
            "tags": payload.get("tags", []),
            "resolution_summary": payload.get("resolution_summary", ""),
            "source": "ledger",
            "based_on_claim_ids": payload.get("based_on_claim_ids", []),
        }
        text = _safe_text(row, list(safe_text_keys))
        index.append({"type": "decision", "id": decision_id, "text": text, "row": row})
    for ev in iterate_events(Path(workspace_root)):
        action = ev.get("action") or ""
        payload = ev.get("payload") or {}
        entry_type: Optional[str] = None
        entry_id: str = ""
        row: Dict[str, Any] = {}
        if action == "OBSERVATION_RECORDED":
            entry_type = "observation"
            entry_id = payload.get("observation_id") or (ev.get("object") or {}).get("id") or ev.get("event_id") or ""
            row = {
                "observation_id": entry_id,
                "title": payload.get("signal_id", ""),
                "summary": payload.get("source", {}).get("type", ""),
                "rationale": payload.get("integrity", {}).get("content_type", ""),
                "notes": payload.get("source", {}),
                "tags": payload.get("labels", []),
                "resolution_summary": payload.get("quality", {}),
                "source": "ledger",
            }
        elif action == "ANOMALY_DETECTED":
            entry_type = "anomaly"
            entry_id = payload.get("anomaly_id") or (ev.get("object") or {}).get("id") or ev.get("event_id") or ""
            row = {
                "anomaly_id": entry_id,
                "title": payload.get("rule_id", ""),
                "summary": payload.get("severity", ""),
                "rationale": payload.get("metrics", {}),
                "notes": payload,
                "tags": [payload.get("severity", "")],
                "resolution_summary": payload.get("rule_id", ""),
                "source": "ledger",
            }
        elif action == "HANDOFF_CREATED":
            entry_type = "handoff"
            entry_id = payload.get("handoff_id") or (ev.get("object") or {}).get("id") or ev.get("event_id") or ""
            row = {
                "handoff_id": entry_id,
                "title": payload.get("ownership_mode", ""),
                "summary": payload.get("priority", ""),
                "rationale": payload.get("work_item_ref", {}),
                "notes": payload,
                "tags": [payload.get("priority", "")],
                "resolution_summary": payload.get("expected_response_by", ""),
                "source": "ledger",
            }
        elif action == "SELF_ASSESSMENT_RECORDED":
            entry_type = "self_assessment"
            entry_id = payload.get("assessment_id") or (ev.get("object") or {}).get("id") or ev.get("event_id") or ""
            row = {
                "decision_id": payload.get("decision_id", ""),
                "title": "self-assessment",
                "summary": str(payload.get("confidence", "")),
                "rationale": payload.get("uncertainty_factors", []),
                "notes": payload.get("risk_flags", []),
                "tags": payload.get("recommended_controls", {}),
                "resolution_summary": payload.get("rationale_artifact_id", ""),
                "source": "ledger",
            }
        elif action.startswith("INCIDENT_"):
            entry_type = "incident"
            entry_id = payload.get("incident_id") or payload.get("candidate_id") or (ev.get("object") or {}).get("id") or ev.get("event_id") or ""
            row = {
                "incident_id": entry_id,
                "title": payload.get("severity", ""),
                "summary": payload.get("status", ""),
                "rationale": payload.get("evidence_refs", []),
                "notes": payload,
                "tags": [payload.get("severity", "")],
                "resolution_summary": payload.get("reason", ""),
                "source": "ledger",
            }
        if entry_type and entry_id:
            text = _safe_text(row, list(safe_text_keys))
            index.append({"type": entry_type, "id": entry_id, "text": text, "row": row})
    return index


def search(
    workspace_root: Path,
    query: str,
    type_filter: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Search index by substring in safe text or exact id match. type_filter: decision, observation, anomaly, handoff, self_assessment."""
    index = build_search_index(Path(workspace_root))
    q = (query or "").strip().lower()
    out = []
    for entry in index:
        if type_filter and entry.get("type") != type_filter:
            continue
        if q in (entry.get("id") or "").lower():
            out.append(entry)
            continue
        if q and q in (entry.get("text") or "").lower():
            out.append(entry)
        elif not q:
            out.append(entry)
    return out[:limit]


def get_decision_links(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    """Cross-link from decision: claims, observations, self_assessment, evaluations, incidents (from materialized)."""
    out: Dict[str, Any] = {"decision_id": decision_id, "claims": [], "observations": [], "self_assessment": None, "evaluations": [], "incidents": []}
    try:
        from hg_core.ledger import facts_meaning
        expl = facts_meaning.explain_decision(decision_id, workspace_root)
        out["claims"] = expl.get("claims") or []
    except Exception:
        pass
    for ev in iterate_events(Path(workspace_root)):
        action = ev.get("action") or ""
        payload = ev.get("payload") or {}
        if action == "OBSERVATION_BOUND" and payload.get("entity_type") == "decision" and payload.get("entity_id") == decision_id:
            out["observations"].append(payload.get("observation_id"))
        elif action == "SELF_ASSESSMENT_RECORDED" and payload.get("decision_id") == decision_id:
            out["self_assessment"] = payload
        elif action == "DECISION_COMMITTED" and (payload.get("decision_id") == decision_id or (ev.get("object") or {}).get("id") == decision_id):
            ev_id = payload.get("evaluation_id") or payload.get("evaluation_id_ref")
            if ev_id:
                out["evaluations"].append(ev_id)
            break
    for ev in iterate_events(Path(workspace_root)):
        action = ev.get("action") or ""
        payload = ev.get("payload") or {}
        if not action.startswith("INCIDENT_"):
            continue
        refs = payload.get("evidence_refs") or []
        if any(isinstance(r, dict) and (r.get("id") == decision_id or (r.get("type") == "decision" and r.get("id") == decision_id)) for r in refs):
            out["incidents"].append(payload)
        elif decision_id in str(refs):
            out["incidents"].append(payload)
    return out


def get_anomaly_links(workspace_root: Path, anomaly_id: str) -> Dict[str, Any]:
    """Cross-link from anomaly: observation_ids, incidents, modulations (from materialized)."""
    out: Dict[str, Any] = {"anomaly_id": anomaly_id, "observation_ids": [], "incidents": [], "modulations": []}
    for ev in iterate_events(Path(workspace_root)):
        action = ev.get("action") or ""
        payload = ev.get("payload") or {}
        if action == "ANOMALY_DETECTED" and (payload.get("anomaly_id") == anomaly_id or ev.get("event_id") == anomaly_id):
            out["observation_ids"] = payload.get("observation_ids") or ([payload["observation_id"]] if payload.get("observation_id") else [])
        elif action.startswith("INCIDENT_"):
            refs = payload.get("evidence_refs") or []
            if anomaly_id in str(refs):
                out["incidents"].append(payload)
        elif action in ("APPLIED_MODULATION_RECORDED", "MODULATION_APPLIED"):
            before = payload.get("before_state") or {}
            if anomaly_id in str(before) or anomaly_id in str(payload.get("after_state") or {}):
                out["modulations"].append(payload)
    return out
