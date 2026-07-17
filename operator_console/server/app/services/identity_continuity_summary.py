from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_gateway.operational_state_ledger import load_operational_json_state


def _extract_timestamp(value: Any) -> str | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("timestamp", "created_at", "wake_completed_at", "window_end_ts", "sleep_completed_at"):
            extracted = _extract_timestamp(value.get(key))
            if extracted:
                return extracted
    return None


def build_identity_continuity_summary(
    *,
    root,
    task_name: str,
    session_target: str,
    binding: dict[str, Any] | None = None,
    memory_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding = binding or {}
    state = {}
    if root is not None and session_target:
        ledger = load_operational_json_state(root, state_key=f"identity_continuity_state:{session_target}")
        state = ledger.get("payload") if isinstance(ledger.get("payload"), dict) else {}

    initialization_memo_present = bool(state.get("initialization_memo_present"))
    wake_receipt_present = bool(state.get("wake_receipt_present"))
    sleep_summary_present = bool(state.get("sleep_summary_present"))
    initialization_memo_path_value = str(state.get("initialization_memo_path") or "").strip()
    initialization_memo_relpath = str(Path(initialization_memo_path_value)) if initialization_memo_path_value else None

    last_wake_at = (
        _extract_timestamp((memory_health or {}).get("last_wake_at"))
        or _extract_timestamp(state.get("last_wake_at"))
    )
    wake_receipt_recorded_at = _extract_timestamp(state.get("wake_receipt_recorded_at"))
    last_sleep_at = (
        _extract_timestamp((memory_health or {}).get("last_sleep_at"))
        or _extract_timestamp(state.get("last_sleep_at"))
    )
    sleep_summary_recorded_at = _extract_timestamp(state.get("sleep_summary_recorded_at"))

    status = "missing"
    if initialization_memo_present and last_wake_at:
        status = "healthy"
    elif initialization_memo_present or last_wake_at or last_sleep_at or str(binding.get("fingerprint_id") or "").strip():
        status = "partial"

    continuity_anchor = str(binding.get("operational_agent_id") or "").strip() or task_name
    return {
        "status": status,
        "continuity_anchor": continuity_anchor,
        "task_name": task_name,
        "session_target": session_target or None,
        "operational_session_target": binding.get("operational_session_target"),
        "memory_namespace": binding.get("memory_namespace"),
        "fingerprint_id": binding.get("fingerprint_id"),
        "compatible_agent_ids": list(binding.get("compatible_agent_ids") or []),
        "compatible_session_targets": list(binding.get("compatible_session_targets") or []),
        "initialization_memo_present": initialization_memo_present,
        "initialization_memo_path": initialization_memo_relpath,
        "wake_receipt_present": wake_receipt_present,
        "sleep_summary_present": sleep_summary_present,
        "last_wake_at": last_wake_at,
        "wake_receipt_recorded_at": wake_receipt_recorded_at,
        "last_sleep_at": last_sleep_at,
        "sleep_summary_recorded_at": sleep_summary_recorded_at,
    }
