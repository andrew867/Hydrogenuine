"""Chapter2 role norms: coordination style and checkpoint list per workflow. Ref: .cursor/plans/autonomy/chapter2 SPEC_ROLE_NORMS."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

COORDINATION_STYLES = ("end-to-end_lead", "pipeline_baton", "parallel_contributors")


def validate_workflow_declaration(decl: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate workflow declaration for coordination_style and checkpoints.
    Returns (True, "") if valid; (False, reason) if invalid.
    pipeline_baton requires non-empty checkpoints list.
    """
    style = decl.get("coordination_style")
    if style is None:
        return True, ""  # optional
    if style not in COORDINATION_STYLES:
        return False, f"invalid_coordination_style_{style}"
    if style == "pipeline_baton":
        checkpoints = decl.get("checkpoints")
        if not isinstance(checkpoints, list) or len(checkpoints) == 0:
            return False, "pipeline_baton_requires_checkpoints"
    return True, ""


def load_coordination_declaration(
    workflow_id: str,
    workspace_root: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Load workflow declaration and return coordination_style and checkpoints (or None)."""
    try:
        from hg_core.task_graph.capability_enforcement import load_workflow_capabilities
        caps = load_workflow_capabilities(workflow_id, workspace_root)
    except Exception:
        caps = None
    if not caps:
        return None
    style = caps.get("coordination_style")
    checkpoints = caps.get("checkpoints")
    if style is None and checkpoints is None:
        return None
    return {"coordination_style": style, "checkpoints": checkpoints or []}


def get_checkpoints_for_workflow(
    workflow_id: str,
    workspace_root: Optional[Path] = None,
) -> List[str]:
    """Return list of checkpoint IDs for this workflow (empty if not baton or not declared)."""
    decl = load_coordination_declaration(workflow_id, workspace_root)
    if not decl or decl.get("coordination_style") != "pipeline_baton":
        return []
    return list(decl.get("checkpoints") or [])


def requires_receipt_at_checkpoint(
    workflow_id: str,
    checkpoint_id: str,
    workspace_root: Optional[Path] = None,
) -> bool:
    """True if workflow is pipeline_baton and checkpoint_id is in its checkpoints list."""
    checkpoints = get_checkpoints_for_workflow(workflow_id, workspace_root)
    return checkpoint_id in checkpoints
