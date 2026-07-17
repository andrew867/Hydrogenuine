"""
Tests for DAG planner: valid goal -> valid DAG; invalid -> diagnostics; example goals.
"""

from pathlib import Path

import pytest

from hg_core.task_graph import (
    DagPlanner,
    PlannerConstraints,
    PlannerResult,
    validate_dag_with_diagnostics,
)


def test_planner_goal_matching_template_produces_valid_dag():
    planner = DagPlanner()
    result = planner.plan("Run a weekly job search diff for agent roles")
    assert result.dag is not None
    assert result.confidence > 0
    assert len(result.diagnostics) == 0
    # DAG must validate
    r = validate_dag_with_diagnostics(result.dag, strict=False)
    assert r["ok"] is True
    assert result.dag["graph_id"] == "planned_job_search_weekly_diff_v1"


def test_planner_research_summary_produces_valid_dag():
    planner = DagPlanner()
    result = planner.plan("Summarize recent research on agent orchestration")
    assert result.dag is not None
    assert len(result.diagnostics) == 0
    r = validate_dag_with_diagnostics(result.dag, strict=False)
    assert r["ok"] is True
    assert result.dag["graph_id"] == "planned_research_summary_v1"
    inputs = result.dag["inputs"]
    assert inputs["answer_style"] == "grounded_summary"
    assert inputs["fetch_page_count"] >= 3


def test_planner_current_events_prompt_routes_to_research_summary():
    planner = DagPlanner()
    result = planner.plan("What's going on today with the US government and Flock cameras everywhere?")
    assert result.dag is not None
    assert len(result.diagnostics) == 0
    assert result.dag["graph_id"] == "planned_research_summary_v1"
    inputs = result.dag["inputs"]
    assert inputs["freshness"] == "pw"
    assert inputs["result_window"] >= 6
    assert inputs["answer_style"] == "news_brief"


def test_planner_comparison_prompt_expands_research_budget():
    planner = DagPlanner()
    result = planner.plan("Compare Anthropic vs OpenAI coding agents and explain the tradeoffs")
    assert result.dag is not None
    inputs = result.dag["inputs"]
    assert inputs["answer_style"] == "comparison"
    assert inputs["result_window"] >= 7
    assert inputs["fetch_page_count"] >= 5
    assert inputs["query_variant_limit"] >= 4
    assert any("review" in variant.lower() for variant in inputs["query_variants"])


def test_planner_generic_workflow_fallback():
    planner = DagPlanner()
    result = planner.plan("Do something arbitrary")
    assert result.dag is not None
    assert len(result.diagnostics) == 0
    r = validate_dag_with_diagnostics(result.dag, strict=False)
    assert r["ok"] is True
    assert result.dag["graph_id"] == "planned_generic_workflow_v1"


def test_planner_invalid_dag_returns_diagnostics():
    # Use a custom template that produces invalid DAG (duplicate node id); override generic_workflow
    def bad_template(goal, context, constraints):
        return {
            "graph_id": "bad",
            "version": "1.0",
            "run_policy": {"max_concurrency": 1},
            "inputs": {},
            "nodes": [
                {"id": "a", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "policy": {}, "checkpoints": {"before": False, "after": False}},
                {"id": "a", "type": "tool", "assigned_entity": "y", "depends_on": [], "inputs": {}, "policy": {}, "checkpoints": {"before": False, "after": False}},
            ],
        }
    planner = DagPlanner(templates={"generic_workflow": bad_template})
    result = planner.plan("do something arbitrary")
    assert result.dag is None
    assert result.confidence == 0.0
    codes = [d.code for d in result.diagnostics]
    assert "DUPLICATE_NODE_ID" in codes


def test_planner_missing_graph_id_returns_diagnostics():
    def no_graph_id_template(goal, context, constraints):
        return {
            "version": "1.0",
            "run_policy": {"max_concurrency": 1},
            "inputs": {},
            "nodes": [{"id": "n1", "type": "tool", "assigned_entity": "x", "depends_on": [], "inputs": {}, "policy": {}, "checkpoints": {"before": False, "after": False}}],
        }
    planner = DagPlanner(templates={"generic_workflow": no_graph_id_template})
    result = planner.plan("no id goal")
    assert result.dag is None
    codes = [d.code for d in result.diagnostics]
    assert "MISSING_GRAPH_ID" in codes


def test_planner_example_goal_01():
    goals_path = Path(__file__).resolve().parent.parent.parent / ".cursor" / "plans" / "dag" / "chapter2" / "examples" / "planner_goals" / "goal_01.json"
    if not goals_path.exists():
        pytest.skip("chapter2 example goals not present")
    import json
    with open(goals_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    goal = data.get("goal", "")
    context = data.get("context", {})
    planner = DagPlanner()
    result = planner.plan(goal, context=context)
    assert result.dag is not None
    assert len(result.diagnostics) == 0
    r = validate_dag_with_diagnostics(result.dag, strict=False)
    assert r["ok"] is True


def test_planner_example_goal_02():
    goals_path = Path(__file__).resolve().parent.parent.parent / ".cursor" / "plans" / "dag" / "chapter2" / "examples" / "planner_goals" / "goal_02.json"
    if not goals_path.exists():
        pytest.skip("chapter2 example goals not present")
    import json
    with open(goals_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    goal = data.get("goal", "")
    context = data.get("context", {})
    planner = DagPlanner()
    result = planner.plan(goal, context=context)
    assert result.dag is not None
    assert len(result.diagnostics) == 0
    r = validate_dag_with_diagnostics(result.dag, strict=False)
    assert r["ok"] is True
