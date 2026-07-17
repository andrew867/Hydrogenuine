from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _runtime_tenant_id() -> str:
    import os

    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _empty_summary() -> dict[str, Any]:
    return {
        "status": "missing",
        "workflow_id": None,
        "coordination_style": None,
        "coordination_style_source": None,
        "coordination_checkpoints": [],
        "run_policy": {},
        "swarm_run_id": None,
        "swarm_role": None,
        "swarm_turn_count": 0,
        "swarm_member_count": 0,
        "swarm_orchestrator_present": False,
        "dominant_relationship_type": None,
        "dominant_engagement_mode": None,
        "top_counterparts": [],
        "recent_swarm_events": [],
        "recent_swarm_members": [],
    }


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _workflow_dag_candidates(task_name: str, binding: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for raw in (
        binding.get("workflow_id"),
        binding.get("operational_family"),
        binding.get("operational_session_target"),
        task_name,
    ):
        value = str(raw or "").strip()
        if not value:
            continue
        for candidate in (
            value,
            value.replace("-", "_"),
            value.replace("_", "-"),
        ):
            if candidate and candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _load_workflow_dag(root: Path | None, task_name: str, binding: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if not root:
        return None, None
    dags_dir = root / "memory" / "automation" / "dags"
    if not dags_dir.exists():
        return None, None
    for candidate in _workflow_dag_candidates(task_name, binding):
        path = dags_dir / f"{candidate}.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload, candidate
    return None, None


def _coordination_style_from_dag(dag: dict[str, Any]) -> tuple[str | None, str | None]:
    if not isinstance(dag, dict):
        return None, None
    declared = str(dag.get("coordination_style") or "").strip()
    if declared:
        return declared, "declared"
    run_policy = dag.get("run_policy") if isinstance(dag.get("run_policy"), dict) else {}
    max_concurrency = run_policy.get("max_concurrency")
    try:
        concurrency = int(max_concurrency)
    except (TypeError, ValueError):
        concurrency = 0
    if concurrency <= 1:
        return "pipeline_baton", "inferred_from_run_policy"
    return "parallel_contributors", "inferred_from_run_policy"


def _dominant_key(counts: dict[str, int]) -> str | None:
    if not counts:
        return None
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def build_crew_dynamics_summary(
    *,
    root: Path | None,
    task_name: str,
    session_target: str,
    binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding = binding or {}
    fingerprint_id = str(binding.get("fingerprint_id") or "").strip()
    if not fingerprint_id:
        return _empty_summary()
    try:
        from hg_gateway.store import get_store
    except Exception:
        return _empty_summary()

    store = get_store()
    if not hasattr(store, "persona_autonomy_list"):
        return _empty_summary()

    try:
        autonomy_rows = store.persona_autonomy_list(
            _runtime_tenant_id(),
            fingerprint_id=fingerprint_id,
            hours=24.0 * 365.0,
            limit=1000,
        )
    except Exception:
        return _empty_summary()
    if not isinstance(autonomy_rows, list):
        return _empty_summary()

    swarm_rows = [row for row in autonomy_rows if isinstance(row, dict) and str(row.get("swarm_run_id") or "").strip()]
    latest_row = max(
        swarm_rows,
        key=lambda row: _parse_timestamp(row.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc),
        default=None,
    )
    active_swarm_run_id = str((latest_row or {}).get("swarm_run_id") or "").strip() or None
    active_swarm_role = str((latest_row or {}).get("swarm_role") or "").strip() or None

    swarm_summary: dict[str, Any] = {}
    if active_swarm_run_id and hasattr(store, "persona_autonomy_swarm_summary"):
        try:
            swarm_summary = store.persona_autonomy_swarm_summary(_runtime_tenant_id(), active_swarm_run_id, hours=24.0 * 365.0) or {}
        except Exception:
            swarm_summary = {}

    naturalness_summary: dict[str, Any] = {}
    if active_swarm_run_id and hasattr(store, "persona_naturalness_swarm_summary"):
        try:
            naturalness_summary = store.persona_naturalness_swarm_summary(_runtime_tenant_id(), active_swarm_run_id, hours=24.0 * 365.0) or {}
        except Exception:
            naturalness_summary = {}

    relationship_counts: dict[str, int] = {}
    counterpart_counts: dict[str, int] = {}
    recent_events: list[dict[str, Any]] = []
    for row in swarm_rows[:50]:
        relationship_type = str(row.get("relationship_type") or "").strip()
        counterpart = str(row.get("counterpart_fingerprint_id") or "").strip()
        engagement_mode = str(row.get("engagement_mode") or "").strip() or None
        if relationship_type:
            relationship_counts[relationship_type] = relationship_counts.get(relationship_type, 0) + 1
        if counterpart:
            counterpart_counts[counterpart] = counterpart_counts.get(counterpart, 0) + 1
        if relationship_type or counterpart or engagement_mode:
            recent_events.append(
                {
                    "created_at": row.get("created_at"),
                    "swarm_run_id": row.get("swarm_run_id"),
                    "swarm_role": row.get("swarm_role"),
                    "relationship_type": relationship_type or None,
                    "counterpart_fingerprint_id": counterpart or None,
                    "engagement_mode": engagement_mode,
                }
            )

    recent_members = []
    if isinstance(swarm_summary.get("members"), list):
        for member in swarm_summary["members"][:5]:
            if not isinstance(member, dict):
                continue
            recent_members.append(
                {
                    "chat_id": member.get("chat_id"),
                    "swarm_role": member.get("swarm_role"),
                    "turn_count": member.get("turn_count"),
                    "relationship_types": member.get("relationship_types") or {},
                    "engagement_modes": member.get("engagement_modes") or {},
                }
            )

    coordination_style = None
    coordination_style_source = None
    coordination_checkpoints: list[str] = []
    run_policy: dict[str, Any] = {}
    workflow_id = None
    dag_payload, workflow_id = _load_workflow_dag(Path(root) if root else None, task_name, binding)
    if isinstance(dag_payload, dict):
        run_policy = dag_payload.get("run_policy") if isinstance(dag_payload.get("run_policy"), dict) else {}
        coordination_style, coordination_style_source = _coordination_style_from_dag(dag_payload)
        checkpoints = dag_payload.get("checkpoints")
        if isinstance(checkpoints, list):
            coordination_checkpoints = [str(item).strip() for item in checkpoints if str(item).strip()]

    total_turns = len(autonomy_rows)
    crew_member_count = len(recent_members) or len(swarm_summary.get("members") or [])
    orchestrator_present = bool(swarm_summary.get("orchestrator"))
    dominant_engagement_mode = None
    if isinstance(naturalness_summary.get("summary"), dict):
        engagement_distribution = naturalness_summary["summary"].get("engagement_distribution")
        if isinstance(engagement_distribution, dict):
            dominant_engagement_mode = _dominant_key({str(k): int(v or 0) for k, v in engagement_distribution.items()})
    if dominant_engagement_mode is None:
        engagement_counts: dict[str, int] = {}
        for row in swarm_rows:
            engagement = str(row.get("engagement_mode") or "").strip()
            if engagement:
                engagement_counts[engagement] = engagement_counts.get(engagement, 0) + 1
        dominant_engagement_mode = _dominant_key(engagement_counts)

    status = "missing"
    if active_swarm_run_id or coordination_style:
        status = "partial"
    if active_swarm_run_id and coordination_style and crew_member_count >= 1:
        status = "healthy"

    return {
        "status": status,
        "workflow_id": workflow_id or None,
        "coordination_style": coordination_style,
        "coordination_style_source": coordination_style_source,
        "coordination_checkpoints": coordination_checkpoints,
        "run_policy": {
            "max_concurrency": run_policy.get("max_concurrency"),
            "failure_mode": run_policy.get("failure_mode"),
            "max_node_executions": run_policy.get("max_node_executions"),
        },
        "swarm_run_id": active_swarm_run_id,
        "swarm_role": active_swarm_role,
        "swarm_turn_count": len(swarm_rows),
        "swarm_member_count": crew_member_count,
        "swarm_orchestrator_present": orchestrator_present,
        "dominant_relationship_type": _dominant_key(relationship_counts),
        "dominant_engagement_mode": dominant_engagement_mode,
        "top_counterparts": [
            {"counterpart_fingerprint_id": counterpart, "count": count}
            for counterpart, count in sorted(counterpart_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
        ],
        "recent_swarm_events": recent_events[:5],
        "recent_swarm_members": recent_members,
        "naturalness_summary": naturalness_summary.get("summary") if isinstance(naturalness_summary.get("summary"), dict) else None,
        "autonomy_summary": swarm_summary.get("summary") if isinstance(swarm_summary.get("summary"), dict) else None,
    }
