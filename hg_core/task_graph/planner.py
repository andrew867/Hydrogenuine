"""
DAG planner: goal + context + constraints -> DAG dict or diagnostics.

Template-first MVP; uses validate_dag_with_diagnostics via an adapter.
Does not execute.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .validator_diagnostics import Diagnostic, validate_dag_with_diagnostics
from .planner_templates import TEMPLATES


def _validator_adapter(dag_dict: Dict[str, Any], strict: bool) -> Dict[str, Any]:
    """Adapter: validate_dag_with_diagnostics -> {ok, errors, warnings} with dict items."""
    result = validate_dag_with_diagnostics(dag_dict, strict=strict)
    return {
        "ok": result["ok"],
        "errors": [d.to_dict() for d in result["errors"]],
        "warnings": [d.to_dict() for d in result["warnings"]],
    }


@dataclass
class PlannerConstraints:
    disallowed_tools: List[str] = field(default_factory=list)
    max_iterations_default: int = 10
    max_node_executions_cap: int = 500
    strict_mode: bool = False
    failure_mode: str = "continue"
    allow_side_effects_in_loops: bool = False


@dataclass
class PlannerResult:
    dag: Optional[Dict[str, Any]]
    diagnostics: List[Diagnostic]
    confidence: float = 0.0


class DagPlanner:
    def __init__(
        self,
        templates: Optional[Dict[str, Callable[..., Dict[str, Any]]]] = None,
        validator: Optional[Callable[[Dict[str, Any], bool], Dict[str, Any]]] = None,
        tool_registry: Optional[Any] = None,
    ):
        self.templates = templates if templates is not None else TEMPLATES
        self.validator = validator if validator is not None else _validator_adapter
        self.tool_registry = tool_registry

    def plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[PlannerConstraints] = None,
    ) -> PlannerResult:
        context = context or {}
        # Inject entity tool awareness into context (Social Media Entity Tools)
        try:
            from hg_core.tools.planner_hints import get_planner_bootstrap_context
            for k, v in get_planner_bootstrap_context().items():
                if k not in context:
                    context[k] = v
        except Exception:
            pass
        constraints = constraints or PlannerConstraints(disallowed_tools=[])
        tname = self._select_template(goal, context)
        if tname not in self.templates:
            return PlannerResult(
                None,
                [Diagnostic("error", "NO_TEMPLATE", f"No template for goal: {goal}")],
                0.0,
            )

        dag = self.templates[tname](goal=goal, context=context, constraints=constraints)
        dag = self._apply_defaults(dag, constraints)

        if self.tool_registry is not None:
            reg = self.tool_registry
            registered_names = {d.name for d in reg.list()}
            for n in dag.get("nodes", []):
                if n.get("type") == "tool":
                    entity = n.get("assigned_entity")
                    if entity not in registered_names:
                        return PlannerResult(
                            None,
                            [
                                Diagnostic(
                                    "error",
                                    "UNREGISTERED_TOOL",
                                    f"Tool node references unregistered tool: {entity!r}",
                                    node_id=n.get("id"),
                                )
                            ],
                            0.0,
                        )

        vr = self.validator(dag, strict=constraints.strict_mode)
        if not vr.get("ok", False):
            diags = [
                Diagnostic(
                    "error",
                    e.get("code", "VALIDATION_ERROR"),
                    e.get("message", ""),
                    e.get("node_id"),
                    e.get("field_path"),
                    e.get("suggestion"),
                )
                for e in vr.get("errors", [])
            ]
            return PlannerResult(None, diags, 0.0)

        return PlannerResult(dag, [], 0.6)

    def _select_template(self, goal: str, context: Optional[Dict[str, Any]] = None) -> str:
        g = goal.lower()
        context = context or {}
        research_hints = (
            "research",
            "summar",
            "search",
            "look up",
            "lookup",
            "find",
            "headline",
            "headlines",
            "news",
            "latest",
            "current",
            "today",
            "this week",
            "what's going on",
            "what is going on",
            "what do you know about",
            "tell me about",
            "compare",
            "comparison",
            "versus",
            "tradeoff",
            "difference",
            "explain",
            "analysis",
        )
        if context.get("attached_documents") and context.get("segment_count", 0) >= 2:
            if any(token in g for token in ("read", "review", "summar", "analy", "chapter", "section", "document", "pdf", "attachment")):
                return "document_review_fanout"
        if ("4claw" in g or "fourclaw" in g) and ("post" in g or "thread" in g):
            return "fourclaw_single_post"
        if "job" in g and ("weekly" in g or "diff" in g):
            return "job_search_weekly_diff"
        if any(token in g for token in research_hints):
            return "research_summary"
        return "generic_workflow"

    def _apply_defaults(self, dag: Dict[str, Any], c: PlannerConstraints) -> Dict[str, Any]:
        dag.setdefault("version", "1.0")
        rp = dag.setdefault("run_policy", {})
        rp.setdefault("max_concurrency", 1)
        rp.setdefault("failure_mode", c.failure_mode)
        rp.setdefault("expression_strict_mode", c.strict_mode)
        rp.setdefault("allow_side_effects_in_loops", c.allow_side_effects_in_loops)
        rp["max_node_executions"] = min(
            int(rp.get("max_node_executions", c.max_node_executions_cap)),
            c.max_node_executions_cap,
        )

        reg = self.tool_registry
        for n in dag.get("nodes", []):
            n.setdefault("checkpoints", {"before": False, "after": False})
            pol = n.setdefault("policy", {})
            pol.setdefault("max_retries", 0)
            pol.setdefault("retry_backoff_ms", 100)
            if n.get("type") == "tool" and reg is not None:
                try:
                    desc = reg.get(n.get("assigned_entity", ""))
                    pol.setdefault("timeout_s", desc.default_timeout_s)
                    pol.setdefault("effect_class", desc.effect_class)
                except KeyError:
                    pol.setdefault("timeout_s", 30)
                    pol.setdefault("effect_class", "read")
            else:
                pol.setdefault("timeout_s", 30 if n.get("type") in ("tool", "agent") else None)
                if n.get("type") == "tool":
                    pol.setdefault("effect_class", "read")
                else:
                    pol.setdefault("effect_class", "none")
            if n.get("type") == "loop":
                pol.setdefault("max_iterations", c.max_iterations_default)
        return dag
