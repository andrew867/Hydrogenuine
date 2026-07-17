from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.constitutional_memory import get_constitutional_root, list_constitutional_roots
from hg_core.drift.api import get_drift_alerts, get_drift_scores


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _parse_ts(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return float("-inf")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _family_matches_target(workflow_family: str | None, *targets: str | None) -> bool:
    family = _normalize_text(workflow_family)
    if not family:
        return False
    tokens = [str(target or "").strip().lower() for target in targets if str(target or "").strip()]
    if not tokens:
        return True
    family_lower = family.lower()
    for token in tokens:
        if token == family_lower:
            return True
        if token.startswith(family_lower):
            return True
        if family_lower in token:
            return True
    return False


def _compact_root(root_row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(root_row, dict):
        return None
    return {
        "root_id": root_row.get("root_id"),
        "workflow_family": root_row.get("workflow_family"),
        "title": root_row.get("title"),
        "root_goal": root_row.get("root_goal"),
        "policy_version_id": root_row.get("policy_version_id"),
        "drift_severity": root_row.get("drift_severity"),
        "status": root_row.get("status"),
        "updated_at": root_row.get("updated_at"),
    }


def _json_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except Exception:
            return [text]
        if isinstance(parsed, list):
            return parsed
        if parsed is None:
            return []
        return [parsed]
    return [value]


def _choose_roots(
    roots: list[dict[str, Any]],
    *,
    workflow_family: str | None = None,
    root_id: str | None = None,
    baseline_root_id: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
    ordered = [row for row in roots if isinstance(row, dict)]
    ordered.sort(key=lambda row: _parse_ts(row.get("updated_at")), reverse=True)
    current = None
    if root_id:
        current = next((row for row in ordered if str(row.get("root_id") or "").strip() == root_id), None)
    if current is None and workflow_family:
        current = next((row for row in ordered if _family_matches_target(workflow_family, row.get("workflow_family"))), None)
    if current is None:
        current = ordered[0] if ordered else None
    baseline = None
    if baseline_root_id:
        baseline = next((row for row in ordered if str(row.get("root_id") or "").strip() == baseline_root_id), None)
    if baseline is None and current is not None:
        current_idx = ordered.index(current) if current in ordered else -1
        if current_idx > 0:
            baseline = ordered[current_idx - 1]
    if baseline is None and len(ordered) > 1:
        baseline = ordered[1]
    if baseline is current:
        baseline = None
    return current, baseline, ordered


def _compare_root_payloads(current: dict[str, Any] | None, baseline: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(current, dict):
        return {
            "status": "missing",
            "summary": "No constitutional root selected.",
            "drift_event_delta": 0,
            "policy_changed": False,
            "constraints_changed": False,
            "subgoals_changed": False,
        }
    if not isinstance(baseline, dict):
        return {
            "status": "current_only",
            "summary": "No baseline available.",
            "drift_event_delta": len(current.get("drift_events") or []),
            "policy_changed": False,
            "constraints_changed": False,
            "subgoals_changed": False,
        }
    current_constraints = _json_list(current.get("material_constraints_json") or current.get("material_constraints"))
    baseline_constraints = _json_list(baseline.get("material_constraints_json") or baseline.get("material_constraints"))
    current_subgoals = _json_list(current.get("approved_subgoals_json") or current.get("approved_subgoals"))
    baseline_subgoals = _json_list(baseline.get("approved_subgoals_json") or baseline.get("approved_subgoals"))
    drift_event_delta = len(current.get("drift_events") or []) - len(baseline.get("drift_events") or [])
    policy_changed = str(current.get("policy_version_id") or "") != str(baseline.get("policy_version_id") or "")
    constraints_changed = list(current_constraints) != list(baseline_constraints)
    subgoals_changed = list(current_subgoals) != list(baseline_subgoals)
    changed_parts: list[str] = []
    if policy_changed:
        changed_parts.append("policy version changed")
    if constraints_changed:
        changed_parts.append("constraints changed")
    if subgoals_changed:
        changed_parts.append("subgoals changed")
    if drift_event_delta:
        changed_parts.append(f"{drift_event_delta:+d} drift events")
    return {
        "status": "changed" if changed_parts else "same",
        "summary": ", ".join(changed_parts) if changed_parts else "No material baseline drift.",
        "drift_event_delta": drift_event_delta,
        "policy_changed": policy_changed,
        "constraints_changed": constraints_changed,
        "subgoals_changed": subgoals_changed,
    }


def _normalize_root_events(root_row: dict[str, Any] | None, *, entity_id: str | None = None) -> list[dict[str, Any]]:
    if not isinstance(root_row, dict):
        return []
    root_info = root_row.get("root") if isinstance(root_row.get("root"), dict) else root_row
    workflow_family = _normalize_text(root_info.get("workflow_family"))
    root_id = _normalize_text(root_info.get("root_id"))
    rows: list[dict[str, Any]] = []
    for event in root_row.get("drift_events") or []:
        if not isinstance(event, dict):
            continue
        severity = _normalize_text(event.get("severity")) or "watch"
        summary = _normalize_text(event.get("summary")) or "Drift detected"
        details = event.get("details_json")
        if not isinstance(details, dict):
            details = {}
        detail = summary
        if details:
            detail = f"{summary} · {', '.join(f'{k}={v}' for k, v in list(details.items())[:3])}"
        rows.append(
            {
                "event_id": event.get("drift_event_id"),
                "timestamp": event.get("created_at"),
                "entity_id": entity_id,
                "workflow_id": workflow_family,
                "root_id": root_id,
                "event_type": "drift.detected",
                "severity": severity,
                "summary": summary,
                "detail": detail,
                "title": "Drift detected",
                "href": f"#/governance?root_id={root_id}" if root_id else "#/governance",
                "payload": {
                    "root_id": root_id,
                    "workflow_family": workflow_family,
                    "severity": severity,
                    "summary": summary,
                    "details": details,
                },
            }
        )
    rows.sort(key=lambda row: _parse_ts(row.get("timestamp")), reverse=True)
    return rows


def get_recent_drift_timeline_events(
    limit: int = 20,
    *,
    entity_id: str | None = None,
    workflow_id: str | None = None,
    root_id: str | None = None,
) -> list[dict[str, Any]]:
    try:
        roots = list_constitutional_roots()
    except Exception:
        return []
    current, _baseline, ordered = _choose_roots(roots, workflow_family=workflow_id, root_id=root_id)
    if root_id and current is None:
        return []
    events: list[dict[str, Any]] = []
    targets = [entity_id, workflow_id]
    root_rows = [current] if current is not None else ordered
    for root_row in root_rows:
        root_id_value = _normalize_text(root_row.get("root_id")) if isinstance(root_row, dict) else None
        if not root_id_value:
            continue
        try:
            detailed = get_constitutional_root(root_id_value)
        except Exception:
            detailed = None
        if not isinstance(detailed, dict):
            continue
        current_root = detailed.get("root") if isinstance(detailed.get("root"), dict) else root_row
        workflow_family = _normalize_text(current_root.get("workflow_family"))
        if workflow_family and _family_matches_target(workflow_family, *targets):
            events.extend(_normalize_root_events(detailed, entity_id=entity_id or workflow_family))
    events.sort(key=lambda row: _parse_ts(row.get("timestamp")), reverse=True)
    return events[:limit]


def build_drift_review_summary(
    *,
    workflow_family: str | None = None,
    root_id: str | None = None,
    baseline_root_id: str | None = None,
    entity_id: str | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    root = _workspace_root()
    if root is None:
        return {
            "status": "missing",
            "workflow_family": workflow_family,
            "root": None,
            "baseline_root": None,
            "comparison": {"status": "missing", "summary": "Workspace unavailable."},
            "recent_drift_events": [],
            "drift_scores": [],
            "active_safeguards": [],
            "max_score": 0.0,
            "recommended_action": None,
        }

    try:
        roots = list_constitutional_roots()
    except Exception:
        roots = []
    current, baseline, ordered = _choose_roots(roots, workflow_family=workflow_family, root_id=root_id, baseline_root_id=baseline_root_id)
    current_compact = _compact_root(current)
    baseline_compact = _compact_root(baseline)
    try:
        drift_scores = get_drift_scores(root, limit=limit)
    except Exception:
        drift_scores = []
    try:
        active_safeguards = get_drift_alerts(root)
    except Exception:
        active_safeguards = []
    recent_drift_events = get_recent_drift_timeline_events(
        limit=limit,
        entity_id=entity_id,
        workflow_id=workflow_family,
        root_id=current_compact.get("root_id") if current_compact else root_id,
    )
    max_score = max((float(row.get("score") or 0.0) for row in drift_scores), default=0.0)
    comparison = _compare_root_payloads(current, baseline)
    if active_safeguards:
        status = "blocked"
    elif recent_drift_events or max_score >= 0.7 or comparison.get("status") in {"current_only", "changed"}:
        status = "watch"
    else:
        status = "healthy"
    recommended_action = None
    if status == "blocked":
        recommended_action = "adjust_policy"
    elif status == "watch":
        recommended_action = "record_drift_review"
    return {
        "status": status,
        "workflow_family": workflow_family,
        "root": current_compact,
        "baseline_root": baseline_compact,
        "comparison": comparison,
        "recent_drift_events": recent_drift_events,
        "drift_scores": drift_scores,
        "active_safeguards": active_safeguards,
        "max_score": max_score,
        "recommended_action": recommended_action,
        "root_count": len(ordered),
    }
