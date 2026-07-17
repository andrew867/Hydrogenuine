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


def _ack_path(root: Path, operational_session_target: str) -> Path:
    return root / "memory" / "automation" / operational_session_target / "continuity_recovery_ack.json"


def load_continuity_recovery_ack(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
) -> dict[str, Any]:
    if root is None:
        return {
            "present": False,
            "acknowledged": False,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "note": None,
            "path": None,
        }
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        return {
            "present": False,
            "acknowledged": False,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "note": None,
            "path": None,
        }
    path = _ack_path(root, operational_session_target)
    state = load_operational_json_state(root, state_key=f"continuity_recovery_ack:{operational_session_target}", legacy_path=path)
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    if not state.get("present"):
        return {
            "present": False,
            "acknowledged": False,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "note": None,
            "path": str(path.relative_to(root)) if path.is_absolute() else str(path),
        }
    return {
        "present": True,
        "acknowledged": True,
        "acknowledged_at": str(payload.get("acknowledged_at") or "").strip() or None,
        "acknowledged_by": str(payload.get("acknowledged_by") or "").strip() or None,
        "note": str(payload.get("note") or "").strip() or None,
        "incident_status": str(payload.get("incident_status") or "").strip() or None,
        "identity_status": str(payload.get("identity_status") or "").strip() or None,
        "path": str(path.relative_to(root)) if path.is_absolute() else str(path),
    }


def save_continuity_recovery_ack(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    acknowledged_by: str | None,
    note: str | None = None,
    continuity_recovery_readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    status = str(continuity_recovery_readiness.get("status") or "").strip().lower()
    if status != "caution":
        raise ValueError("continuity recovery acknowledgment is only allowed for caution state")
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        raise ValueError("operational_session_target is required")
    path = _ack_path(root, operational_session_target)
    payload = {
        "acknowledged_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "acknowledged_by": str(acknowledged_by or "operator").strip() or "operator",
        "note": str(note or "").strip() or None,
        "incident_status": continuity_recovery_readiness.get("incident_status"),
        "identity_status": continuity_recovery_readiness.get("identity_status"),
        "blocking": list(continuity_recovery_readiness.get("blocking") or []),
        "cautions": list(continuity_recovery_readiness.get("cautions") or []),
        "summary": continuity_recovery_readiness.get("summary"),
    }
    save_operational_json_state(
        root,
        state_key=f"continuity_recovery_ack:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return load_continuity_recovery_ack(root=root, binding=binding, session_target=operational_session_target)
