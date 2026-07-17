from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state


def _operational_session_target(binding: dict[str, Any] | None, session_target: str | None = None) -> str:
    binding = binding or {}
    explicit = str(binding.get("operational_session_target") or "").strip()
    platform = str(binding.get("platform") or "").strip()
    if explicit and platform:
        return f"{explicit}-{platform}"
    if explicit:
        return explicit
    fallback = str(session_target or "").strip()
    if fallback:
        return fallback
    agent_id = str(binding.get("operational_agent_id") or "").strip()
    if agent_id:
        return f"automation-{agent_id}"
    return ""


def _path(root: Path, operational_session_target: str) -> Path:
    return root / "memory" / "automation" / operational_session_target / "operational_resume_checkpoint.json"



def load_operational_resume_checkpoint(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
) -> dict[str, Any]:
    if root is None:
        return {
            "present": False,
            "approved": False,
            "approved_at": None,
            "approved_by": None,
            "task_checks_snapshot": [],
            "path": None,
        }
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        return {
            "present": False,
            "approved": False,
            "approved_at": None,
            "approved_by": None,
            "task_checks_snapshot": [],
            "path": None,
        }
    path = _path(root, operational_session_target)
    state = load_operational_json_state(root, state_key=f"operational_resume_checkpoint:{operational_session_target}", legacy_path=path)
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    if not state.get("present"):
        return {
            "present": False,
            "approved": False,
            "approved_at": None,
            "approved_by": None,
            "note": None,
            "task_checks_snapshot": [],
            "path": str(path.relative_to(root)) if path.is_absolute() else str(path),
        }
    invalidated_at = str(payload.get("invalidated_at") or "").strip() or None
    task_checks_snapshot = payload.get("task_checks_snapshot")
    if not isinstance(task_checks_snapshot, list):
        task_checks_snapshot = []
    return {
        "present": True,
        "approved": not bool(invalidated_at),
        "approved_at": str(payload.get("approved_at") or "").strip() or None,
        "approved_by": str(payload.get("approved_by") or "").strip() or None,
        "note": str(payload.get("note") or "").strip() or None,
        "resume_summary": str(payload.get("resume_summary") or "").strip() or None,
        "task_checks_snapshot": task_checks_snapshot,
        "invalidated": bool(invalidated_at),
        "invalidated_at": invalidated_at,
        "invalidated_reason": str(payload.get("invalidated_reason") or "").strip() or None,
        "path": str(path.relative_to(root)) if path.is_absolute() else str(path),
    }


def save_operational_resume_checkpoint(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    approved_by: str | None,
    note: str | None = None,
    operational_resume_governance_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operational_resume_governance_summary = operational_resume_governance_summary if isinstance(operational_resume_governance_summary, dict) else {}
    status = str(operational_resume_governance_summary.get("status") or "").strip().lower()
    if status != "ready":
        raise ValueError("operational resume checkpoint can only be approved when operational resume governance is ready")
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        raise ValueError("operational_session_target is required")
    path = _path(root, operational_session_target)
    payload = {
        "approved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "approved_by": str(approved_by or "operator").strip() or "operator",
        "note": str(note or "").strip() or None,
        "resume_summary": operational_resume_governance_summary.get("summary"),
        "required_actions": list(operational_resume_governance_summary.get("required_actions") or []),
        "task_checks_snapshot": list(operational_resume_governance_summary.get("task_checks") or []),
        "invalidated_at": None,
        "invalidated_reason": None,
    }
    save_operational_json_state(
        root,
        state_key=f"operational_resume_checkpoint:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return load_operational_resume_checkpoint(root=root, binding=binding, session_target=operational_session_target)


def ensure_operational_resume_checkpoint_validity(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    operational_resume_governance_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operational_resume_governance_summary = operational_resume_governance_summary if isinstance(operational_resume_governance_summary, dict) else {}
    existing = load_operational_resume_checkpoint(root=root, binding=binding, session_target=session_target)
    if root is None or not existing.get("present") or existing.get("invalidated"):
        return {**existing, "created": False}
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        return {**existing, "created": False}
    current_task_checks = {
        str(task_check.get("task_name") or "").strip(): task_check
        for task_check in (operational_resume_governance_summary.get("task_checks") or [])
        if isinstance(task_check, dict) and str(task_check.get("task_name") or "").strip()
    }
    prior_task_checks = {
        str(task_check.get("task_name") or "").strip(): task_check
        for task_check in (existing.get("task_checks_snapshot") or [])
        if isinstance(task_check, dict) and str(task_check.get("task_name") or "").strip()
    }
    if prior_task_checks and not set(prior_task_checks).issubset(set(current_task_checks)):
        return {**existing, "created": False}
    reason = None
    status = str(operational_resume_governance_summary.get("status") or "").strip().lower()
    if status != "ready":
        reason = "operational_resume_no_longer_ready"
    if reason is None:
        for task_name, current_task_check in current_task_checks.items():
            prior_task_check = prior_task_checks.get(task_name)
            if not isinstance(prior_task_check, dict):
                continue
            if str(current_task_check.get("rebuild_recorded_at") or "").strip() != str(prior_task_check.get("rebuild_recorded_at") or "").strip():
                reason = "new_rebuild_recorded_after_resume_approval"
                break
    if reason is None:
        return {**existing, "created": False}
    path = _path(root, operational_session_target)
    state = load_operational_json_state(root, state_key=f"operational_resume_checkpoint:{operational_session_target}", legacy_path=path)
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    payload["invalidated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload["invalidated_reason"] = reason
    payload["resume_summary"] = operational_resume_governance_summary.get("summary")
    payload["required_actions"] = list(operational_resume_governance_summary.get("required_actions") or [])
    payload["task_checks_snapshot"] = list(operational_resume_governance_summary.get("task_checks") or [])
    save_operational_json_state(
        root,
        state_key=f"operational_resume_checkpoint:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return {**load_operational_resume_checkpoint(root=root, binding=binding, session_target=operational_session_target), "created": True}
