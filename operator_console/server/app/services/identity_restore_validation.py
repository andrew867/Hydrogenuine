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
    return root / "memory" / "automation" / operational_session_target / "identity_restore_validation.json"


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_identity_restore_validation(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    identity_continuity_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if root is None or not operational_session_target:
        return {
            "status": "unavailable",
            "required": False,
            "verified": False,
            "recorded": False,
            "path": None,
        }
    path = _validation_path(root, operational_session_target)
    state = load_operational_json_state(
        root,
        state_key=f"identity_restore_validation:{operational_session_target}",
        legacy_path=path,
    )
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    recorded_at = str(payload.get("restore_recorded_at") or "").strip() or None
    verified_at = str(payload.get("verified_at") or "").strip() or None
    status = "not_required"
    required = False
    continuity_status = str(identity_continuity_summary.get("status") or "").strip().lower()
    wake_receipt_present = bool(identity_continuity_summary.get("wake_receipt_present"))
    sleep_summary_present = bool(identity_continuity_summary.get("sleep_summary_present"))
    if recorded_at:
        required = True
        if verified_at:
            status = "validated"
        elif continuity_status == "missing":
            status = "blocked"
        else:
            status = "pending"
    summary = "identity_restore_not_required"
    if status == "validated":
        summary = "identity_restore_validated"
    elif status == "pending":
        summary = "verify_identity_restore_continuity"
    elif status == "blocked":
        summary = "identity_restore_continuity_missing"
    return {
        "status": status,
        "required": required,
        "recorded": bool(recorded_at),
        "verified": bool(verified_at),
        "restore_recorded_at": recorded_at,
        "restore_recorded_by": str(payload.get("restore_recorded_by") or "").strip() or None,
        "restore_note": str(payload.get("restore_note") or "").strip() or None,
        "verified_at": verified_at,
        "verified_by": str(payload.get("verified_by") or "").strip() or None,
        "verification_note": str(payload.get("verification_note") or "").strip() or None,
        "wake_receipt_present": wake_receipt_present,
        "sleep_summary_present": sleep_summary_present,
        "continuity_status": continuity_status or None,
        "summary": summary,
        "path": str(path),
    }


def record_identity_restore_event(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    recorded_by: str | None = None,
    note: str | None = None,
    restored_at: str | None = None,
) -> dict[str, Any]:
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        raise ValueError("operational_session_target is required")
    payload = {
        "restore_recorded_at": str(restored_at or "").strip() or _iso_now(),
        "restore_recorded_by": str(recorded_by or "operator").strip() or "operator",
        "restore_note": str(note or "").strip() or None,
    }
    path = _validation_path(root, operational_session_target)
    save_operational_json_state(
        root,
        state_key=f"identity_restore_validation:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return load_identity_restore_validation(
        root=root,
        binding=binding,
        session_target=session_target,
        identity_continuity_summary={},
    )


def verify_identity_restore(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    verified_by: str | None = None,
    note: str | None = None,
    identity_continuity_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        raise ValueError("operational_session_target is required")
    if not identity_continuity_summary.get("wake_receipt_present") or not identity_continuity_summary.get("sleep_summary_present"):
        raise ValueError("identity restore validation requires wake receipt and sleep summary")
    path = _validation_path(root, operational_session_target)
    state = load_operational_json_state(
        root,
        state_key=f"identity_restore_validation:{operational_session_target}",
        legacy_path=path,
    )
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    if not payload.get("restore_recorded_at"):
        raise ValueError("identity restore event not recorded")
    payload["verified_at"] = _iso_now()
    payload["verified_by"] = str(verified_by or "operator").strip() or "operator"
    payload["verification_note"] = str(note or "").strip() or None
    save_operational_json_state(
        root,
        state_key=f"identity_restore_validation:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return load_identity_restore_validation(
        root=root,
        binding=binding,
        session_target=session_target,
        identity_continuity_summary=identity_continuity_summary,
    )
