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
    return root / "memory" / "automation" / operational_session_target / "identity_resume_closeout.json"


def load_identity_resume_closeout(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
) -> dict[str, Any]:
    if root is None:
        return {"present": False, "closed_out": False, "closed_out_at": None, "path": None}
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        return {"present": False, "closed_out": False, "closed_out_at": None, "path": None}
    path = _path(root, operational_session_target)
    state = load_operational_json_state(
        root,
        state_key=f"identity_resume_closeout:{operational_session_target}",
        legacy_path=path,
    )
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    if not state.get("present"):
        return {
            "present": False,
            "closed_out": False,
            "closed_out_at": None,
            "observed_at": None,
            "path": str(path.relative_to(root)) if path.is_absolute() else str(path),
        }
    return {
        "present": True,
        "closed_out": True,
        "closed_out_at": str(payload.get("closed_out_at") or "").strip() or None,
        "observed_at": str(payload.get("observed_at") or "").strip() or None,
        "path": str(path.relative_to(root)) if path.is_absolute() else str(path),
    }


def ensure_identity_resume_closeout(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    identity_resume_observation: dict[str, Any] | None = None,
    continuity_recovery_readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root if isinstance(root, Path) else None
    identity_resume_observation = identity_resume_observation if isinstance(identity_resume_observation, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    existing = load_identity_resume_closeout(root=root, binding=binding, session_target=session_target)
    if existing.get("closed_out"):
        return {**existing, "created": False}
    if root is None:
        return {**existing, "created": False}
    if not continuity_recovery_readiness.get("recovery_closeout_complete"):
        return {**existing, "created": False}
    if not identity_resume_observation.get("observation_complete"):
        return {**existing, "created": False}
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        return {**existing, "created": False}
    path = _path(root, operational_session_target)
    payload = {
        "closed_out_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "observed_at": identity_resume_observation.get("observed_at"),
        "summary": identity_resume_observation.get("summary"),
    }
    save_operational_json_state(
        root,
        state_key=f"identity_resume_closeout:{operational_session_target}",
        payload=payload,
        legacy_path=path,
    )
    return {**load_identity_resume_closeout(root=root, binding=binding, session_target=session_target), "created": True}
