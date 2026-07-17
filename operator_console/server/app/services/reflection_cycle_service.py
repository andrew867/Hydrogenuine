from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from hg_core.materializers.metacognition_metrics import run as run_metacognition_metrics
from hg_core.metacognition import write_reflection_artifact
from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state

from .activity_service import get_recent_activity
from .entities_service import list_entities
from .confidence_summary import build_confidence_summary
from .self_model_summary import build_self_model_summary
from .presence_initiative_summary import build_presence_initiative_summary
from .identity_continuity_summary import build_identity_continuity_summary
from .operational_resume_governance_summary import build_operational_resume_governance_summary
from .commitment_summary import build_commitment_summary
from .action_rationale_summary import build_action_rationale_summary
from .bounded_autonomy_policy import build_bounded_autonomy_policy_summary
from .crew_dynamics_summary import build_crew_dynamics_summary
from .affect_action_summary import build_affect_action_summary


STATE_KEY = "reflection_cycle_state"
DEFAULT_COOLDOWN_SECONDS = {
    "memory_consolidation": 6 * 60 * 60,
    "timeline_reconciliation": 2 * 60 * 60,
    "identity_review": 4 * 60 * 60,
    "counterfactual_rehearsal": 12 * 60 * 60,
}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _gateway_state(root: Path) -> dict[str, Any]:
    state = load_operational_json_state(root, state_key=STATE_KEY, legacy_path=root / "memory" / "reflections" / "cycle_state.json")
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    return payload or {}


def _set_gateway_state(root: Path, payload: dict[str, Any]) -> None:
    save_operational_json_state(root, state_key=STATE_KEY, payload=payload, legacy_path=root / "memory" / "reflections" / "cycle_state.json")


def _last_run(payload: dict[str, Any], cycle_name: str) -> str | None:
    cycle = payload.get(cycle_name) if isinstance(payload.get(cycle_name), dict) else {}
    value = str(cycle.get("last_run_at") or "").strip()
    return value or None


def _cycle_state(payload: dict[str, Any], cycle_name: str) -> dict[str, Any]:
    cycle = payload.get(cycle_name) if isinstance(payload.get(cycle_name), dict) else {}
    return cycle if isinstance(cycle, dict) else {}


def _is_due(payload: dict[str, Any], cycle_name: str, *, cooldown_seconds: int, force: bool) -> bool:
    if force:
        return True
    last_run = _last_run(payload, cycle_name)
    if not last_run:
        return True
    try:
        last = datetime.fromisoformat(last_run.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return True
    return datetime.now(UTC) - last >= timedelta(seconds=cooldown_seconds)


def _cooldown_remaining_seconds(payload: dict[str, Any], cycle_name: str, *, cooldown_seconds: int) -> int | None:
    last_run = _last_run(payload, cycle_name)
    if not last_run:
        return None
    try:
        last = datetime.fromisoformat(last_run.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None
    elapsed = (datetime.now(UTC) - last).total_seconds()
    remaining = int(cooldown_seconds - elapsed)
    return max(0, remaining)


def _load_confidence_snapshot(root: Path) -> dict[str, Any]:
    identity_summary = build_identity_continuity_summary(root=root, task_name="", session_target="")
    operational_resume_summary = build_operational_resume_governance_summary(
        root=root,
        binding={},
        task_names=[],
        continuity_recovery_readiness=identity_summary,
        continuity_repair_plan={},
    )
    bounded_autonomy_summary = build_bounded_autonomy_policy_summary(
        agency_control_summary={},
        continuity_recovery_readiness=identity_summary,
        operational_resume_governance_summary=operational_resume_summary,
        operational_resume_checkpoint={},
        identity_restore_validation={},
        supervised_resume_validation={},
    )
    confidence = build_confidence_summary(
        self_model_summary=build_self_model_summary(),
        presence_initiative_summary=build_presence_initiative_summary(root=root, task_name="", session_target=""),
        continuity_recovery_readiness=identity_summary,
        operational_resume_governance_summary=operational_resume_summary,
        operational_resume_checkpoint={},
        bounded_autonomy_policy_summary=bounded_autonomy_summary,
        commitment_summary=build_commitment_summary(root=root, task_name="", session_target=""),
        action_rationale_summary=build_action_rationale_summary(root=root, task_name="", session_target="", binding={}, research_delivery_summary=None, agency_control_summary={}),
        identity_continuity_summary=identity_summary,
        agency_control_summary={},
    )
    return confidence


def _reflection_links(root: Path) -> list[dict[str, Any]]:
    return [
        {"kind": "activity", "href": "#/activity", "label": "Recent activity"},
        {"kind": "entities", "href": "#/entities", "label": "Entities"},
        {"kind": "operational-personas", "href": "#/operational-personas", "label": "Operational personas"},
        {"kind": "governance", "href": "#/governance", "label": "Governance"},
    ]


def get_reflection_cycle_summary(root: Path) -> dict[str, Any]:
    root = Path(root)
    state = _gateway_state(root)
    now = _now()
    cycles: list[dict[str, Any]] = []
    for cycle_name, cooldown in DEFAULT_COOLDOWN_SECONDS.items():
        cycle = _cycle_state(state, cycle_name)
        cycles.append(
            {
                "cycle": cycle_name,
                "title": cycle.get("title") or cycle_name.replace("_", " ").title(),
                "artifact_id": cycle.get("artifact_id"),
                "status": cycle.get("last_status") or ("due" if _is_due(state, cycle_name, cooldown_seconds=cooldown, force=False) else "cooling_down"),
                "last_run_at": cycle.get("last_run_at"),
                "last_success_at": cycle.get("last_success_at"),
                "last_error_at": cycle.get("last_error_at"),
                "last_error": cycle.get("last_error"),
                "cooldown_seconds": cooldown,
                "cooldown_remaining_seconds": _cooldown_remaining_seconds(state, cycle_name, cooldown_seconds=cooldown),
                "due": _is_due(state, cycle_name, cooldown_seconds=cooldown, force=False),
                "verification_status": cycle.get("verification_status") or "provisional",
            }
        )
    return {
        "ok": True,
        "ts": now,
        "cycles": cycles,
        "state": state,
        "materializer": state.get("materializer") if isinstance(state.get("materializer"), dict) else {},
    }


def run_reflection_cycles(root: Path, *, force: bool = False) -> dict[str, Any]:
    root = Path(root)
    now = _now()
    state = _gateway_state(root)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    recent_activity = get_recent_activity(limit_runs=24, limit_decisions=24, projection_view="expanded")
    entities = list_entities()
    confidence = _load_confidence_snapshot(root)
    if not isinstance(recent_activity, dict):
        recent_activity = {}
    if not isinstance(entities, list):
        entities = []

    # Ensure the metacognition materializer is fresh before summarizing.
    try:
        run_metacognition_metrics(root, rebuild=True)
        state["materializer"] = {
            "last_run_at": now,
            "last_status": "completed",
            "last_error": None,
            "last_error_at": None,
        }
    except Exception as exc:
        state["materializer"] = {
            "last_run_at": now,
            "last_status": "failed",
            "last_error": str(exc),
            "last_error_at": now,
        }
        errors.append(
            {
                "cycle": "materializer",
                "title": "Metacognition materializer",
                "error": str(exc),
                "status": "failed",
            }
        )

    cycles = [
        ("memory_consolidation", "Memory consolidation cycle", {
            "activity_counts": recent_activity.get("counts") or {},
            "evidence_timeline": recent_activity.get("evidence_timeline") or {},
            "confidence": confidence,
        }),
        ("timeline_reconciliation", "Timeline reconciliation cycle", {
            "timeline": recent_activity.get("timeline") or [],
            "since_last_wake": recent_activity.get("since_last_wake") or {},
            "evidence_timeline": recent_activity.get("evidence_timeline") or {},
        }),
        ("identity_review", "Identity review cycle", {
            "entity_count": len(entities),
            "healthy_entities": len([item for item in entities if str((item.get("memory_summary") or {}).get("status") or "").lower() == "healthy"]),
            "reflection_statuses": [str((item.get("profile") or {}).get("reflection_status") or {}).lower() for item in entities],
            "confidence": confidence,
        }),
    ]
    if os.getenv("HG_REFLECTION_COUNTERFACTUAL", "").strip().lower() in {"1", "true", "yes", "on"}:
        cycles.append((
            "counterfactual_rehearsal",
            "Counterfactual rehearsal cycle",
            {
                "enabled": True,
                "note": "feature-flagged counterfactual reflection rehearsal",
                "confidence": confidence,
                "sample_paths": [row.get("href") for row in (recent_activity.get("evidence_timeline") or {}).get("timeline", [])[:4] if isinstance(row, dict) and row.get("href")],
            },
        ))

    for cycle_name, title, findings in cycles:
        cooldown = DEFAULT_COOLDOWN_SECONDS[cycle_name]
        if not _is_due(state, cycle_name, cooldown_seconds=cooldown, force=force):
            continue
        payload = {
            "summary": title,
            "findings_json": findings,
            "source_event_ids": [row.get("event_id") for row in (recent_activity.get("timeline") or [])[:6] if isinstance(row, dict) and row.get("event_id")],
            "source_memory_ids": [row.get("entity_id") for row in entities[:6] if isinstance(row, dict) and row.get("entity_id")],
            "source_links": _reflection_links(root),
            "confidence": float((confidence or {}).get("confidence_score") or 0) / 100.0,
            "verification_status": "provisional",
            "reviewed_by": None,
            "promoted_at": None,
        }
        artifact_id = f"reflection:{cycle_name}:{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}"
        try:
            artifact = write_reflection_artifact(
                root,
                artifact_id,
                payload,
                source_event_ids=payload["source_event_ids"],
                source_memory_ids=payload["source_memory_ids"],
                source_links=payload["source_links"],
                confidence=payload["confidence"],
                verification_status=payload["verification_status"],
                title=title,
                change_summary=f"scheduled {cycle_name}",
            )
            state[cycle_name] = {
                "last_run_at": now,
                "last_success_at": now,
                "artifact_id": artifact.get("artifact_id") or artifact_id,
                "title": title,
                "last_status": "completed",
                "verification_status": payload["verification_status"],
                "last_error": None,
                "last_error_at": None,
            }
            results.append({
                "cycle": cycle_name,
                "artifact_id": artifact.get("artifact_id") or artifact_id,
                "title": title,
                "status": "completed",
            })
        except Exception as exc:
            state[cycle_name] = {
                "last_run_at": now,
                "last_status": "failed",
                "title": title,
                "artifact_id": None,
                "verification_status": payload["verification_status"],
                "last_error": str(exc),
                "last_error_at": now,
            }
            errors.append({
                "cycle": cycle_name,
                "title": title,
                "error": str(exc),
                "status": "failed",
            })
    if results:
        _set_gateway_state(root, state)
    elif errors or state.get("materializer"):
        _set_gateway_state(root, state)
    return {"ok": True, "cycles": results, "errors": errors, "state": state, "ts": now, "summary": get_reflection_cycle_summary(root)}
