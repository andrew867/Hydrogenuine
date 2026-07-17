from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from ..core.auth import require_api_key

try:
    from hg_core.task_graph.planner import PlannerConstraints
    from hg_core.task_graph.planner_templates import TEMPLATES
except Exception as exc:  # pragma: no cover
    PlannerConstraints = None
    TEMPLATES = {}

router = APIRouter()


class TemplateRequest(BaseModel):
    goal: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


def _build_template(template_id: str, goal: Optional[str], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "template not found"})
    if PlannerConstraints is None:
        raise HTTPException(status_code=500, detail={"code": "TEMPLATE_UNAVAILABLE", "message": "planner unavailable"})
    constraints = PlannerConstraints()
    g = goal or f"Template: {template_id}"
    ctx = context or {}
    return TEMPLATES[template_id](goal=g, context=ctx, constraints=constraints)


@router.get("")
def list_templates(_=Depends(require_api_key)):
    items = []
    for name, fn in TEMPLATES.items():
        doc = (fn.__doc__ or "").strip()
        try:
            dag = _build_template(name, None, None)
            graph_id = dag.get("graph_id")
            node_count = len(dag.get("nodes", []))
        except Exception:
            graph_id = None
            node_count = None
        items.append({
            "template_id": name,
            "description": doc.splitlines()[0] if doc else None,
            "graph_id": graph_id,
            "node_count": node_count,
        })
    return {"ok": True, "templates": items}


@router.get("/{template_id}")
def get_template(template_id: str, goal: Optional[str] = None, _=Depends(require_api_key)):
    dag = _build_template(template_id, goal, None)
    return {"ok": True, "template_id": template_id, "dag": dag}


@router.post("/{template_id}/instantiate")
def instantiate_template(template_id: str, payload: TemplateRequest, _=Depends(require_api_key)):
    dag = _build_template(template_id, payload.goal, payload.context)
    return {"ok": True, "template_id": template_id, "dag": dag}
