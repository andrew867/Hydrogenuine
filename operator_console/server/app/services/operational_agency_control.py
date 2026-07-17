from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from hg_core.autonomy_config import get_autonomy_config
from hg_gateway import keystore_repo
from hg_gateway.db import _get_db_path, get_connection


VALID_AGENCY_CONTROL_MODES = {"normal", "review_only", "held"}
VALID_OUTBOUND_LANE_POLICIES = {"unrestricted", "replies_only", "drafts_only", "blocked"}
OUTBOUND_BUDGET_ARTIFACT_TYPES = ("post_proof", "reply_proof", "challenge_proof")


def _relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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


def _control_path(root: Path, operational_session_target: str) -> Path:
    return root / "memory" / "automation" / operational_session_target / "agency_control.json"


def _recent_outbound_budget_usage(*, operational_agent_id: str, window_hours: int) -> tuple[int, str | None]:
    if not operational_agent_id:
        return 0, None
    account_ids = [
        str(account.get("social_account_id") or "").strip()
        for account in keystore_repo.social_account_list(tenant_id="default")
        if str(account.get("entity_scope") or "").strip() == operational_agent_id
    ]
    account_ids = [account_id for account_id in account_ids if account_id]
    if not account_ids:
        return 0, None
    placeholders = ",".join("?" for _ in account_ids)
    try:
        with get_connection(_get_db_path()) as conn:
            row = conn.execute(
                f"""SELECT COUNT(*), MIN(created_at)
                    FROM proof_artifacts
                    WHERE related_kind = 'social_account'
                      AND related_id IN ({placeholders})
                      AND artifact_type IN ({",".join("?" for _ in OUTBOUND_BUDGET_ARTIFACT_TYPES)})
                      AND datetime(created_at) >= datetime('now', ?)""",
                tuple(account_ids) + tuple(OUTBOUND_BUDGET_ARTIFACT_TYPES) + (f"-{int(window_hours)} hours",),
            ).fetchone()
    except Exception:
        return 0, None
    try:
        count = int(row[0] or 0) if row else 0
        oldest = str(row[1] or "").strip() or None if row else None
        return count, oldest
    except Exception:
        return 0, None


def _recent_outbound_action_count(*, operational_agent_id: str, window_hours: int) -> int:
    count, _ = _recent_outbound_budget_usage(operational_agent_id=operational_agent_id, window_hours=window_hours)
    return count


def load_operational_agency_control(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
) -> dict[str, Any]:
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    config = get_autonomy_config()
    default_summary = {
        "status": "default",
        "mode": "normal",
        "reason": None,
        "updated_at": None,
        "updated_by": None,
        "outbound_lane_policy": "unrestricted",
        "allowed_outbound_modes": ["auto-post", "engage", "publish"],
        "outbound_actions_window_hours": 24,
        "daily_outbound_budget": None,
        "recent_outbound_action_count": 0,
        "outbound_budget_remaining": None,
        "outbound_budget_exhausted": False,
        "outbound_budget_next_reset_at": None,
        "operator_hold": False,
        "review_required": False,
        "effective_mode": "normal",
        "global_outbound_safety_gate_enabled": bool(config.get("outbound_safety_gate_enabled")),
        "global_entity_dag_change_control": config.get("entity_dag_change_control"),
        "operational_session_target": operational_session_target or None,
        "path": None,
    }
    if not operational_session_target:
        return default_summary
    path = _control_path(root, operational_session_target)
    default_summary["path"] = _relpath(path, root)
    if not path.exists():
        return default_summary
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            **default_summary,
            "status": "invalid",
            "effective_mode": "review_only",
            "review_required": True,
        }
    mode = str(payload.get("mode") or "normal").strip().lower()
    if mode not in VALID_AGENCY_CONTROL_MODES:
        mode = "review_only"
    outbound_lane_policy = str(payload.get("outbound_lane_policy") or "unrestricted").strip().lower()
    if outbound_lane_policy not in VALID_OUTBOUND_LANE_POLICIES:
        outbound_lane_policy = "drafts_only"
    window_hours = int(payload.get("outbound_actions_window_hours") or 24)
    if window_hours < 1:
        window_hours = 24
    raw_budget = payload.get("daily_outbound_budget")
    daily_outbound_budget = None if raw_budget in {None, ""} else int(raw_budget)
    if daily_outbound_budget is not None and daily_outbound_budget < 0:
        daily_outbound_budget = 0
    operational_agent_id = str((binding or {}).get("operational_agent_id") or "").strip()
    recent_outbound_action_count, oldest_outbound_action_at = _recent_outbound_budget_usage(
        operational_agent_id=operational_agent_id,
        window_hours=window_hours,
    )
    outbound_budget_remaining = None
    outbound_budget_exhausted = False
    outbound_budget_next_reset_at = None
    if daily_outbound_budget is not None:
        outbound_budget_remaining = max(0, daily_outbound_budget - recent_outbound_action_count)
        outbound_budget_exhausted = recent_outbound_action_count >= daily_outbound_budget
        if outbound_budget_exhausted and oldest_outbound_action_at:
            try:
                oldest_dt = datetime.fromisoformat(oldest_outbound_action_at.replace("Z", "+00:00"))
                if oldest_dt.tzinfo is None:
                    oldest_dt = oldest_dt.replace(tzinfo=UTC)
                outbound_budget_next_reset_at = (oldest_dt.astimezone(UTC) + timedelta(hours=window_hours)).isoformat().replace("+00:00", "Z")
            except ValueError:
                outbound_budget_next_reset_at = None
    allowed_outbound_modes = ["auto-post", "engage", "publish"]
    if outbound_lane_policy == "replies_only":
        allowed_outbound_modes = ["engage"]
    elif outbound_lane_policy in {"drafts_only", "blocked"}:
        allowed_outbound_modes = []
    return {
        **default_summary,
        "status": "configured",
        "mode": mode,
        "reason": str(payload.get("reason") or "").strip() or None,
        "updated_at": str(payload.get("updated_at") or "").strip() or None,
        "updated_by": str(payload.get("updated_by") or "").strip() or None,
        "outbound_lane_policy": outbound_lane_policy,
        "allowed_outbound_modes": allowed_outbound_modes,
        "outbound_actions_window_hours": window_hours,
        "daily_outbound_budget": daily_outbound_budget,
        "recent_outbound_action_count": recent_outbound_action_count,
        "outbound_budget_remaining": outbound_budget_remaining,
        "outbound_budget_exhausted": outbound_budget_exhausted,
        "outbound_budget_next_reset_at": outbound_budget_next_reset_at,
        "operator_hold": mode == "held",
        "review_required": mode in {"held", "review_only"},
        "effective_mode": mode,
    }


def save_operational_agency_control(
    *,
    root: Path,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
    mode: str,
    reason: str | None = None,
    updated_by: str | None = None,
    outbound_lane_policy: str | None = None,
    daily_outbound_budget: int | None = None,
    outbound_actions_window_hours: int | None = None,
) -> dict[str, Any]:
    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in VALID_AGENCY_CONTROL_MODES:
        raise ValueError(f"mode must be one of {sorted(VALID_AGENCY_CONTROL_MODES)}")
    normalized_lane_policy = str(outbound_lane_policy or "unrestricted").strip().lower()
    if normalized_lane_policy not in VALID_OUTBOUND_LANE_POLICIES:
        raise ValueError(f"outbound_lane_policy must be one of {sorted(VALID_OUTBOUND_LANE_POLICIES)}")
    normalized_budget = None if daily_outbound_budget is None else int(daily_outbound_budget)
    if normalized_budget is not None and normalized_budget < 0:
        raise ValueError("daily_outbound_budget must be >= 0")
    normalized_window_hours = int(outbound_actions_window_hours or 24)
    if normalized_window_hours < 1:
        raise ValueError("outbound_actions_window_hours must be >= 1")
    operational_session_target = _operational_session_target(binding, session_target=session_target)
    if not operational_session_target:
        raise ValueError("operational_session_target is required")
    path = _control_path(root, operational_session_target)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": normalized_mode,
        "reason": str(reason or "").strip() or None,
        "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "updated_by": str(updated_by or "operator").strip() or "operator",
        "outbound_lane_policy": normalized_lane_policy,
        "daily_outbound_budget": normalized_budget,
        "outbound_actions_window_hours": normalized_window_hours,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return load_operational_agency_control(root=root, binding=binding, session_target=operational_session_target)


def build_agency_control_summary(
    *,
    root: Path | None,
    binding: dict[str, Any] | None = None,
    session_target: str | None = None,
) -> dict[str, Any]:
    if root is None:
        config = get_autonomy_config()
        return {
            "status": "unavailable",
            "mode": "normal",
            "reason": None,
            "updated_at": None,
            "updated_by": None,
            "outbound_lane_policy": "unrestricted",
            "allowed_outbound_modes": ["auto-post", "engage", "publish"],
            "outbound_actions_window_hours": 24,
            "daily_outbound_budget": None,
            "recent_outbound_action_count": 0,
            "outbound_budget_remaining": None,
            "outbound_budget_exhausted": False,
            "outbound_budget_next_reset_at": None,
            "operator_hold": False,
            "review_required": False,
            "effective_mode": "normal",
            "global_outbound_safety_gate_enabled": bool(config.get("outbound_safety_gate_enabled")),
            "global_entity_dag_change_control": config.get("entity_dag_change_control"),
            "operational_session_target": None,
            "path": None,
        }
    return load_operational_agency_control(root=root, binding=binding, session_target=session_target)
