from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state


def _operational_session_target(binding: dict[str, Any] | None, session_target: str | None = None) -> str:
    binding = binding or {}
    explicit = str(binding.get("operational_session_target") or "").strip()
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
    return root / "memory" / "automation" / operational_session_target / "post_rebuild_continuity_check.json"


def _normalize_timestamp(raw_value: str | None) -> str:
    candidate = str(raw_value or "").strip()
    if not candidate:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00")).astimezone(UTC)
        return parsed.isoformat().replace("+00:00", "Z")
    except ValueError:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _compare_timestamps(left: str | None, right: str | None) -> int:
    left_value = str(left or "").strip()
    right_value = str(right or "").strip()
    if not left_value and not right_value:
        return 0
    if not left_value:
        return -1
    if not right_value:
        return 1
    try:
        left_dt = datetime.fromisoformat(left_value.replace("Z", "+00:00"))
        right_dt = datetime.fromisoformat(right_value.replace("Z", "+00:00"))
        if left_dt < right_dt:
            return -1
        if left_dt > right_dt:
            return 1
        return 0
    except ValueError:
        if left_value < right_value:
            return -1
        if left_value > right_value:
            return 1
        return 0


def _raw_state(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    if root is None:
        return ({}, None)
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        return ({}, None)
    path = _path(root, operational_session_target)
    state = load_operational_json_state(
        root,
        state_key=f"post_rebuild_continuity_check:{operational_session_target}",
        legacy_path=path,
    )
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    return (payload, str(path.relative_to(root)) if path.is_absolute() else str(path))


def build_post_rebuild_continuity_check(
    *,
    raw_state: dict[str, Any] | None,
    identity_continuity_summary: dict[str, Any] | None,
    continuity_recovery_readiness: dict[str, Any] | None,
    path: str | None = None,
) -> dict[str, Any]:
    raw_state = raw_state if isinstance(raw_state, dict) else {}
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}

    rebuild_recorded_at = str(raw_state.get("rebuild_recorded_at") or "").strip() or None
    verified_at = str(raw_state.get("verified_at") or "").strip() or None
    identity_status = str(identity_continuity_summary.get("status") or "").strip().lower()
    readiness_status = str(continuity_recovery_readiness.get("status") or "").strip().lower()

    blockers: list[str] = []
    cautions: list[str] = []
    verified = False
    verification_required = bool(rebuild_recorded_at)

    if not rebuild_recorded_at:
        status = "not_required"
        summary = "no_rebuild_recorded"
    else:
        if identity_status == "missing":
            blockers.append("identity_continuity_missing")
        if readiness_status == "blocked":
            blockers.append("continuity_recovery_blocked")
        if _compare_timestamps(verified_at, rebuild_recorded_at) < 0:
            cautions.append("verification_after_rebuild_required")
        if blockers:
            status = "blocked"
            summary = blockers[0]
        elif cautions:
            status = "pending"
            summary = cautions[0]
        else:
            status = "verified"
            verified = True
            summary = "post_rebuild_continuity_verified"

    return {
        "present": bool(rebuild_recorded_at or verified_at),
        "status": status,
        "verification_required": verification_required,
        "verified": verified,
        "rebuild_recorded_at": rebuild_recorded_at,
        "rebuild_recorded_by": str(raw_state.get("rebuild_recorded_by") or "").strip() or None,
        "rebuild_note": str(raw_state.get("rebuild_note") or "").strip() or None,
        "verified_at": verified_at,
        "verified_by": str(raw_state.get("verified_by") or "").strip() or None,
        "verify_note": str(raw_state.get("verify_note") or "").strip() or None,
        "continuity_status_at_verification": str(raw_state.get("continuity_status_at_verification") or "").strip() or None,
        "identity_status_at_verification": str(raw_state.get("identity_status_at_verification") or "").strip() or None,
        "blocking": blockers,
        "cautions": cautions,
        "summary": summary,
        "path": path,
    }


def load_post_rebuild_continuity_check(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    identity_continuity_summary: dict[str, Any] | None = None,
    continuity_recovery_readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_state, path = _raw_state(root=root, binding=binding, session_target=session_target)
    return build_post_rebuild_continuity_check(
        raw_state=raw_state,
        identity_continuity_summary=identity_continuity_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        path=path,
    )


def record_post_rebuild_event(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    recorded_by: str | None = None,
    note: str | None = None,
    rebuilt_at: str | None = None,
) -> dict[str, Any]:
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        raise ValueError("operational_session_target is required")
    path = _path(root, operational_session_target)
    payload = {
        "rebuild_recorded_at": _normalize_timestamp(rebuilt_at),
        "rebuild_recorded_by": str(recorded_by or "operator").strip() or "operator",
        "rebuild_note": str(note or "").strip() or None,
        "verified_at": None,
        "verified_by": None,
        "verify_note": None,
        "continuity_status_at_verification": None,
        "identity_status_at_verification": None,
    }
    save_operational_json_state(
        root,
        state_key=f"post_rebuild_continuity_check:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return payload


def verify_post_rebuild_continuity(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    verified_by: str | None = None,
    note: str | None = None,
    identity_continuity_summary: dict[str, Any] | None = None,
    continuity_recovery_readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    readiness_status = str(continuity_recovery_readiness.get("status") or "").strip().lower()
    if readiness_status == "blocked":
        raise ValueError("post-rebuild continuity verification is blocked until continuity recovery is no longer blocked")
    if not bool(identity_continuity_summary.get("initialization_memo_present")):
        raise ValueError("post-rebuild continuity verification requires initialization memo continuity")
    if not bool(identity_continuity_summary.get("wake_receipt_present")):
        raise ValueError("post-rebuild continuity verification requires a wake receipt")
    raw_state, _ = _raw_state(root=root, binding=binding, session_target=session_target)
    rebuild_recorded_at = str(raw_state.get("rebuild_recorded_at") or "").strip()
    if not rebuild_recorded_at:
        raise ValueError("post-rebuild continuity verification requires a recorded rebuild event")
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        raise ValueError("operational_session_target is required")
    path = _path(root, operational_session_target)
    payload = {
        **raw_state,
        "rebuild_recorded_at": rebuild_recorded_at,
        "verified_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "verified_by": str(verified_by or "operator").strip() or "operator",
        "verify_note": str(note or "").strip() or None,
        "continuity_status_at_verification": readiness_status or None,
        "identity_status_at_verification": str(identity_continuity_summary.get("status") or "").strip().lower() or None,
    }
    save_operational_json_state(
        root,
        state_key=f"post_rebuild_continuity_check:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return payload
