"""
Control Surface Pack 9: Onboarding wizard — steps 1–7, session state.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

WIZARD_STEPS = [
    {"step": 1, "name": "template", "title": "Choose template"},
    {"step": 2, "name": "structure", "title": "Define structure"},
    {"step": 3, "name": "trust", "title": "Trust and governance"},
    {"step": 4, "name": "connectors", "title": "Connectors"},
    {"step": 5, "name": "presets", "title": "Presets and steering"},
    {"step": 6, "name": "simulation", "title": "Simulation"},
    {"step": 7, "name": "go_live", "title": "Go-live checks"},
]


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sessions_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "onboarding_sessions"


def start_wizard_session(
    workspace_root: Path,
    template_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Start onboarding session. Returns { session_id, step: 1, step_name, next_step, state }."""
    workspace_root = Path(workspace_root)
    root = _sessions_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    ts = _iso_ts()
    session_id = "wiz_" + hashlib.sha256(ts.encode()).hexdigest()[:16]
    state: Dict[str, Any] = {
        "session_id": session_id,
        "current_step": 1,
        "started_ts": ts,
        "payload": {"template": template_id or ""},
    }
    path = root / f"{session_id}.json"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    step_info = WIZARD_STEPS[0]
    return {
        "session_id": session_id,
        "step": 1,
        "step_name": step_info["name"],
        "title": step_info["title"],
        "next_step": 2,
        "state": state,
    }


def wizard_step(
    workspace_root: Path,
    session_id: str,
    step: int,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Submit wizard step. Returns { session_id, step, step_name, title, next_step, state, done }.
    When step 7 is submitted with success, done=True.
    """
    workspace_root = Path(workspace_root)
    root = _sessions_root(workspace_root)
    path = root / f"{session_id}.json"
    if not path.exists():
        return {"error": "session_not_found", "session_id": session_id}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"error": "session_invalid", "session_id": session_id}

    current = state.get("current_step", 1)
    if step != current:
        return {"error": "wrong_step", "expected_step": current, "session_id": session_id}

    state.setdefault("payload", {})
    state["payload"].update(payload)
    state["updated_ts"] = _iso_ts()
    if step == 7:
        state["done"] = True
        next_step = None
        state["current_step"] = 7
    else:
        next_step = step + 1
        state["current_step"] = next_step
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    step_info = WIZARD_STEPS[step - 1] if 1 <= step <= len(WIZARD_STEPS) else {"name": "", "title": ""}
    return {
        "session_id": session_id,
        "step": step,
        "step_name": step_info.get("name", ""),
        "title": step_info.get("title", ""),
        "next_step": next_step,
        "state": state,
        "done": state.get("done", False),
    }
