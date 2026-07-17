from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state


def _operational_session_target(binding: dict[str, Any] | None, session_target: str | None = None) -> str:
    binding = binding if isinstance(binding, dict) else {}
    explicit = str(binding.get("operational_session_target") or "").strip()
    if explicit:
        return explicit
    fallback = str(session_target or "").strip()
    if fallback:
        return fallback
    operational_agent_id = str(binding.get("operational_agent_id") or "").strip()
    if operational_agent_id:
        return f"automation-{operational_agent_id}"
    return ""


def _validation_path(root: Path, operational_session_target: str) -> Path:
    return root / "memory" / "automation" / operational_session_target / "supervised_resume_validation.json"


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_supervised_resume_validation(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    post_rebuild_continuity_check: dict[str, Any] | None = None,
    continuity_recovery_readiness: dict[str, Any] | None = None,
    continuity_recovery_ack: dict[str, Any] | None = None,
    identity_restore_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    post_rebuild_continuity_check = post_rebuild_continuity_check if isinstance(post_rebuild_continuity_check, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    continuity_recovery_ack = continuity_recovery_ack if isinstance(continuity_recovery_ack, dict) else {}
    identity_restore_validation = identity_restore_validation if isinstance(identity_restore_validation, dict) else {}
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if root is None or not operational_session_target:
        return {"status": "unavailable", "required": False, "validated": False, "path": None}
    path = _validation_path(root, operational_session_target)
    state = load_operational_json_state(
        root,
        state_key=f"supervised_resume_validation:{operational_session_target}",
        legacy_path=path,
    )
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    requirement_times: list[datetime] = []
    completed_checks: list[str] = []
    open_checks: list[str] = []
    if bool(post_rebuild_continuity_check.get("verified")):
        completed_checks.append("post_rebuild_continuity_verified")
        parsed = _parse_iso(post_rebuild_continuity_check.get("verified_at"))
        if parsed:
            requirement_times.append(parsed)
    if bool(continuity_recovery_ack.get("acknowledged")):
        completed_checks.append("continuity_recovery_acknowledged")
        parsed = _parse_iso(continuity_recovery_ack.get("acknowledged_at"))
        if parsed:
            requirement_times.append(parsed)
    if bool(identity_restore_validation.get("verified")):
        completed_checks.append("identity_restore_validated")
        parsed = _parse_iso(identity_restore_validation.get("verified_at"))
        if parsed:
            requirement_times.append(parsed)
    elif bool(identity_restore_validation.get("required")):
        open_checks.append("identity_restore_validated")
    required = bool(requirement_times or identity_restore_validation.get("required"))
    latest_requirement_at = max(requirement_times).isoformat().replace("+00:00", "Z") if requirement_times else None
    validated_at = str(payload.get("validated_at") or "").strip() or None
    validated_at_dt = _parse_iso(validated_at)
    latest_requirement_dt = _parse_iso(latest_requirement_at)
    validated = bool(validated_at_dt and (latest_requirement_dt is None or validated_at_dt >= latest_requirement_dt))
    if latest_requirement_dt and not validated:
        for item in completed_checks:
            if item not in open_checks:
                open_checks.append(item)
        completed_checks = []
    if not required:
        status = "not_required"
    elif validated:
        status = "validated"
    else:
        status = "pending"
    if not validated and required and not open_checks:
        open_checks.append("run_supervised_resume_validation")
    return {
        "status": status,
        "required": required,
        "validated": validated,
        "validated_at": validated_at,
        "validated_by": str(payload.get("validated_by") or "").strip() or None,
        "validation_note": str(payload.get("validation_note") or "").strip() or None,
        "latest_requirement_at": latest_requirement_at,
        "open_checks": open_checks,
        "completed_checks": completed_checks,
        "summary": "run_supervised_resume_validation" if status == "pending" else ("supervised_resume_validated" if status == "validated" else "supervised_resume_not_required"),
        "path": str(path),
    }


def save_supervised_resume_validation(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    validated_by: str | None = None,
    note: str | None = None,
    supervised_resume_validation: dict[str, Any] | None = None,
    operational_resume_governance_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    supervised_resume_validation = supervised_resume_validation if isinstance(supervised_resume_validation, dict) else {}
    operational_resume_governance_summary = operational_resume_governance_summary if isinstance(operational_resume_governance_summary, dict) else {}
    if str(operational_resume_governance_summary.get("status") or "").strip().lower() == "blocked":
        raise ValueError("supervised resume validation is blocked until operational resume governance is no longer blocked")
    if not bool(supervised_resume_validation.get("required")):
        raise ValueError("supervised resume validation is not currently required")
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        raise ValueError("operational_session_target is required")
    payload = {
        "validated_at": _iso_now(),
        "validated_by": str(validated_by or "operator").strip() or "operator",
        "validation_note": str(note or "").strip() or None,
        "latest_requirement_at": supervised_resume_validation.get("latest_requirement_at"),
    }
    path = _validation_path(root, operational_session_target)
    save_operational_json_state(
        root,
        state_key=f"supervised_resume_validation:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return load_supervised_resume_validation(
        root=root,
        binding=binding,
        session_target=operational_session_target,
        post_rebuild_continuity_check=operational_resume_governance_summary.get("post_rebuild_continuity_check"),
        continuity_recovery_readiness=operational_resume_governance_summary.get("continuity_recovery_readiness"),
        continuity_recovery_ack=operational_resume_governance_summary.get("continuity_recovery_ack"),
        identity_restore_validation=operational_resume_governance_summary.get("identity_restore_validation"),
    )
