"""
Capability model per workflow (S1): deny undeclared scopes/destinations/tools.

Workflow declaration (JSON) lists read_scopes, write_scopes, allowed_destinations, allowed_tools.
check_allowed(workflow_id, action_type, scope_or_dest) returns (True, "") or (False, reason).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

WORKFLOW_DECLARATIONS_DIR = "memory/automation/workflows"


def _declaration_path(workspace_root: Path, workflow_id: str) -> Path:
    safe_id = workflow_id.replace("/", "_").replace("\\", "_")
    return workspace_root / WORKFLOW_DECLARATIONS_DIR / f"{safe_id}.json"


def load_workflow_capabilities(
    workflow_id: str,
    workspace_root: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    Load workflow declaration (read_scopes, write_scopes, allowed_destinations, allowed_tools).
    Returns None if no declaration found (caller may allow or deny by default).
    """
    try:
        from hg_lib.config import get_workspace_root
        root = Path(workspace_root or get_workspace_root())
    except Exception:
        root = Path(workspace_root or ".")
    path = _declaration_path(root, workflow_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def check_allowed(
    workflow_id: str,
    action_type: str,
    scope_or_dest: str,
    workspace_root: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Check if (workflow_id, action_type, scope_or_dest) is allowed by workflow declaration.

    action_type: "read" | "write" | "destination" | "tool"
    scope_or_dest: path/category for read/write, destination name for destination, tool name for tool.

    Returns (True, "") if allowed, (False, reason) if denied.
    When no declaration exists, default is deny (least-privilege).
    """
    caps = load_workflow_capabilities(workflow_id, workspace_root)
    if caps is None:
        return False, "no_workflow_declaration"

    if action_type == "read":
        allowed = caps.get("read_scopes") or []
    elif action_type == "write":
        allowed = caps.get("write_scopes") or []
    elif action_type == "destination":
        allowed = caps.get("allowed_destinations") or []
    elif action_type == "tool":
        allowed = caps.get("allowed_tools") or []
    else:
        return False, f"unknown_action_type_{action_type}"

    if not isinstance(allowed, list):
        allowed = []
    if scope_or_dest in allowed:
        return True, ""
    return False, f"undeclared_{action_type}_{scope_or_dest}"
