"""
Steering API service: steering events, authority config, steering profiles.
Reads steering telemetry from the shared gateway store and config/profile data from overseer files.
L10: submit_steering_event() writes to hg_realtime steering store (Phase 8).
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from hg_gateway.shared_storage import list_steering_telemetry


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def get_steering_events(limit: int = 100) -> list[dict[str, Any]]:
    """Read last `limit` steering telemetry events from the shared gateway store (newest first)."""
    events = list_steering_telemetry(limit)
    return events[:limit]


def get_authority_config() -> dict[str, Any]:
    """Load authority config from memory/overseer/authority-config.json; default if missing or malformed."""
    root = _workspace_root()
    if not root:
        return {"mode": "moderate", "thresholds": {}}
    path = root / "memory" / "overseer" / "authority-config.json"
    if not path.exists():
        return {"mode": "moderate", "thresholds": {}}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"mode": "moderate", "thresholds": {}}


def list_steering_profiles() -> list[str]:
    """List persisted profile IDs plus known registry agents so the UI is not blank by default."""
    root = _workspace_root()
    profile_ids: set[str] = set()
    if root:
        dir_path = root / "memory" / "overseer" / "steering"
        if dir_path.is_dir():
            profile_ids.update(f.stem for f in dir_path.glob("*.json"))
    try:
        from hg_core.job_registry import list_tasks

        profile_ids.update(str(task).strip() for task in list_tasks() if str(task).strip())
    except Exception:
        pass
    return sorted(profile_ids)


def submit_steering_event(
    run_id: str,
    kind: str,
    payload: Optional[Dict[str, Any]] = None,
    tenant_id: str = "default",
    actor_id: str = "api",
    correlation_id: str = "",
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit a steering event (cancel/pause/resume/inject) via hg_realtime. Returns { ok, steering_id } or { ok: False, error }."""
    try:
        from hg_realtime.steering import get_default_store, set_default_store, SqliteSteeringAdapter, SteeringEvent
    except ImportError as e:
        return {"ok": False, "error": str(e)}
    store = get_default_store()
    if store is None:
        adapter = SqliteSteeringAdapter()
        store = adapter.store
        set_default_store(store)
    evt = SteeringEvent(
        steering_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id or "",
        run_id=run_id,
        node_id=node_id,
        kind=(kind or "inject").strip().lower(),
        payload=payload if isinstance(payload, dict) else {},
    )
    try:
        store.submit(evt)
        return {"ok": True, "steering_id": evt.steering_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _sanitize_agent_id(agent_id: str) -> bool:
    if ".." in agent_id or "/" in agent_id or "\\" in agent_id:
        return False
    return True


def get_steering_profile(agent_id: str) -> dict[str, Any] | None:
    """Load steering profile for agent from memory/overseer/steering/{agent_id}.json. Returns None if not found."""
    root = _workspace_root()
    if not root or not _sanitize_agent_id(agent_id):
        return None
    try:
        from hg_overseer.overseer_core.steering_store import load_profile
        return load_profile(agent_id, root)
    except Exception:
        pass
    path = root / "memory" / "overseer" / "steering" / f"{agent_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def put_steering_profile(agent_id: str, profile: dict[str, Any], updated_by: str = "") -> bool:
    """Save steering profile. Returns True on success."""
    root = _workspace_root()
    if not root or not _sanitize_agent_id(agent_id):
        return False
    try:
        from hg_overseer.overseer_core.steering_store import save_profile
        save_profile(agent_id, profile, root, updated_by=updated_by)
        return True
    except Exception:
        return False


def get_default_steering_profile(agent_id: str) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "mode": "default",
        "priority": "normal",
        "constraints": {},
        "notes": "No persisted steering profile yet.",
    }


def get_constitution(agent_id: str) -> str | None:
    """Load Style Constitution for agent. Returns None if invalid agent_id."""
    root = _workspace_root()
    if not root or not _sanitize_agent_id(agent_id):
        return None
    try:
        from hg_overseer.overseer_core.steering_store import load_constitution
        return load_constitution(agent_id, root)
    except Exception:
        return ""


def put_constitution(agent_id: str, content: str) -> bool:
    root = _workspace_root()
    if not root or not _sanitize_agent_id(agent_id):
        return False
    try:
        from hg_overseer.overseer_core.steering_store import save_constitution
        save_constitution(agent_id, content, root)
        return True
    except Exception:
        return False


def get_origin_myths(agent_id: str) -> list[str] | None:
    """Load Origin Myths for agent. Returns None if invalid agent_id."""
    root = _workspace_root()
    if not root or not _sanitize_agent_id(agent_id):
        return None
    try:
        from hg_overseer.overseer_core.steering_store import load_origin_myths
        return load_origin_myths(agent_id, root)
    except Exception:
        return []


def put_origin_myths(agent_id: str, myths: list[str]) -> bool:
    root = _workspace_root()
    if not root or not _sanitize_agent_id(agent_id):
        return False
    try:
        from hg_overseer.overseer_core.steering_store import save_origin_myths
        save_origin_myths(agent_id, myths, root)
        return True
    except Exception:
        return False
