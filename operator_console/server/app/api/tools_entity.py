"""
Tools invoke-plan API (Social Media Entity Tools).
POST /api/v1/tools/invoke-plan: entity_id, user_request, context -> proposed_steps, required_approvals, selected_tools.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from hg_core.tools import get_default_registry

router = APIRouter(tags=["tools-entity"])


class InvokePlanRequestBody(BaseModel):
    entity_id: str
    user_request: str
    context: Dict[str, Any] = {}


@router.post("/invoke-plan")
def tools_invoke_plan(body: InvokePlanRequestBody) -> Dict[str, Any]:
    """
    Produce a proposed plan (proposed_steps, required_approvals, selected_tools) for an entity
    given user_request and context. Uses tool registry and planner hints; does not execute.
    """
    reg = get_default_registry()
    # Build a minimal proposed plan from registry: list tools that might apply.
    # Full integration with DagPlanner can be added later; here we return structure.
    tools_for_planner = reg.list_for_planner()
    # Simple heuristic: if request mentions a platform, suggest that tool
    request_lower = (body.user_request or "").lower()
    selected_tools: List[str] = []
    for t in tools_for_planner:
        tid = t.get("tool_id") or ""
        if not tid:
            continue
        if "reddit" in request_lower and tid == "social_reddit":
            selected_tools.append(tid)
        elif "twitter" in request_lower or "x " in request_lower or " post" in request_lower:
            if tid == "social_x":
                selected_tools.append(tid)
        elif "facebook" in request_lower and tid == "social_facebook":
            selected_tools.append(tid)
        elif "browser" in request_lower or "web" in request_lower and tid == "browser_runtime":
            selected_tools.append(tid)
    if not selected_tools and tools_for_planner:
        selected_tools = [t.get("tool_id") for t in tools_for_planner if t.get("requires_approval")][:3]
    proposed_steps: List[Dict[str, Any]] = []
    required_approvals: List[str] = []
    for i, tid in enumerate(selected_tools[:5]):
        step_id = f"step_{i+1}"
        defn = reg.get(tid)
        if not defn:
            continue
        proposed_steps.append({
            "step_id": step_id,
            "tool_id": tid,
            "description": body.user_request[:200] if body.user_request else "",
            "requires_approval": getattr(defn, "requires_approval", True),
            "inputs": {},
        })
        if getattr(defn, "requires_approval", True):
            required_approvals.append(step_id)
    return {
        "entity_id": body.entity_id,
        "user_request": body.user_request,
        "context": body.context,
        "proposed_steps": proposed_steps,
        "required_approvals": required_approvals,
        "selected_tools": selected_tools,
    }
