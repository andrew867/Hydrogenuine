"""
Planner templates: goal + context + constraints -> DAG dict.

Templates produce dicts compatible with DAG.from_dict and the main validator.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _dedupe_strings(values: List[str], limit: int = 5) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        normalized = re.sub(r"\s+", " ", str(value or "")).strip()
        lowered = normalized.lower()
        if not normalized or lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(normalized)
        if len(ordered) >= limit:
            break
    return ordered


def _quoted_phrases(text: str) -> List[str]:
    return [match.strip() for match in re.findall(r'"([^"]+)"', text or "") if match.strip()]


def _comparison_sides(text: str) -> List[str]:
    parts = re.split(r"\b(?:vs|versus)\b", text or "", maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return []
    left = re.sub(r"\bcompare\b", "", parts[0], flags=re.IGNORECASE).strip(" ,.-")
    right = re.sub(r"\b(?:and|the|tradeoffs?|differences?)\b", "", parts[1], flags=re.IGNORECASE).strip(" ,.-")
    if not left or not right:
        return []
    return [left, right]


def _research_inputs(goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
    supplied = dict(context.get("inputs", {}) or {})
    topic = str(supplied.get("topic") or goal).strip() or goal
    query = str(supplied.get("query") or topic or goal).strip() or goal
    kind = str(supplied.get("kind") or "search").strip() or "search"
    region_name = str(supplied.get("region_name") or "").strip()
    is_local = bool(supplied.get("is_local"))
    combined = " ".join(part for part in (goal, topic, query) if part).lower()
    wants_current = kind == "news" or any(
        token in combined
        for token in ("today", "tonight", "latest", "current", "this week", "breaking", "what's going on", "what is going on")
    )
    wants_compare = any(token in combined for token in ("compare", "comparison", "versus", " vs ", "pros and cons", "tradeoff", "difference"))
    wants_explain = any(
        token in combined
        for token in (" why ", " how ", "timeline", "background", "explain", "what happened", "impact", "analysis")
    )
    result_window = 6 if wants_current else 5
    fetch_page_count = 4 if wants_current else 3
    if wants_compare:
        result_window += 2
        fetch_page_count += 2
    elif wants_explain:
        result_window += 1
        fetch_page_count += 1
    if region_name and is_local:
        result_window = max(4, result_window - 1)
    result_window = _clamp(result_window, 4, 8)
    fetch_page_count = _clamp(fetch_page_count, 2, 6)
    query_variants: List[str] = [query]
    if topic and topic.lower() != query.lower():
        query_variants.append(topic)
    if wants_current and "latest" not in query.lower() and "today" not in query.lower():
        query_variants.append(f"{query} latest")
    if wants_explain:
        query_variants.append(f"{topic} background")
        query_variants.append(f"{topic} timeline")
    quoted = _quoted_phrases(combined)
    if quoted:
        query_variants.append(" ".join(f'"{phrase}"' for phrase in quoted[:2]))
    if wants_compare:
        sides = _comparison_sides(query or topic)
        if len(sides) == 2:
            left, right = sides
            query_variants.append(f"{left} vs {right}")
            query_variants.append(f"{left} review")
            query_variants.append(f"{right} review")
    if region_name and is_local and region_name.lower() not in query.lower():
        query_variants.append(f"{query} {region_name}")
    query_variants = _dedupe_strings(query_variants, limit=5)
    answer_style = "grounded_summary"
    if wants_current:
        answer_style = "news_brief"
    if wants_compare:
        answer_style = "comparison"
    elif wants_explain:
        answer_style = "explainer"
    return {
        "topic": topic,
        "query": query,
        "kind": kind,
        "tool_name": supplied.get("tool_name"),
        "is_local": is_local,
        "region_name": region_name,
        "freshness": "pw" if wants_current else "any",
        "result_window": result_window,
        "fetch_page_count": fetch_page_count,
        "query_variants": query_variants,
        "query_variant_limit": 4 if wants_compare or wants_explain else 3,
        "answer_style": answer_style,
    }


def template_document_review_fanout(goal: str, context: Dict[str, Any], constraints: Any) -> Dict[str, Any]:
    inputs = context.get("inputs", {})
    segment_ids = inputs.get("segment_ids") or []
    segment_labels = inputs.get("segment_labels") or []
    return {
        "graph_id": "planned_document_review_fanout_v1",
        "version": "1.0",
        "run_policy": {
            "max_concurrency": max(1, min(len(segment_ids) or 1, 8)),
            "failure_mode": constraints.failure_mode,
            "expression_strict_mode": constraints.strict_mode,
            "allow_side_effects_in_loops": constraints.allow_side_effects_in_loops,
            "max_node_executions": constraints.max_node_executions_cap,
            "max_total_runtime_s": 300,
        },
        "inputs": {
            "goal": goal,
            "document_id": inputs.get("document_id"),
            "filename": inputs.get("filename"),
            "segment_ids": segment_ids,
            "segment_labels": segment_labels,
        },
        "nodes": [
            {
                "id": "segment_fanout",
                "type": "loop",
                "assigned_entity": "loop_controller",
                "depends_on": [],
                "inputs": {
                    "condition": True,
                    "body": ["segment_review"],
                },
                "policy": {"max_iterations": max(1, len(segment_ids) or 1)},
            },
            {
                "id": "segment_review",
                "type": "agent",
                "assigned_entity": "worker_agent",
                "depends_on": ["segment_fanout"],
                "inputs": {
                    "goal": "$graph.inputs.goal",
                    "document_id": "$graph.inputs.document_id",
                    "segment_ids": "$graph.inputs.segment_ids",
                    "segment_labels": "$graph.inputs.segment_labels",
                },
                "outputs": {"result": {}},
                "checkpoints": {"before": True, "after": True},
                "policy": {"timeout_s": 180},
            },
            {
                "id": "reduce",
                "type": "agent",
                "assigned_entity": "summarizer_agent",
                "depends_on": ["segment_fanout"],
                "inputs": {"goal": "$graph.inputs.goal"},
                "outputs": {"result": {}},
                "checkpoints": {"before": True, "after": True},
                "policy": {"timeout_s": 120},
            },
        ],
    }

def template_job_search_weekly_diff(goal: str, context: Dict[str, Any], constraints: Any) -> Dict[str, Any]:
    inputs = context.get("inputs", {
        "companies": ["Anthropic", "OpenAI", "xAI"],
        "state_path": "./.job_state/last.json",
        "recency_days": 7,
        "min_fit_score": 70,
        "top_n": 15,
    })
    return {
        "graph_id": "planned_job_search_weekly_diff_v1",
        "version": "1.0",
        "run_policy": {
            "max_concurrency": 1,
            "failure_mode": constraints.failure_mode,
            "expression_strict_mode": constraints.strict_mode,
            "allow_side_effects_in_loops": constraints.allow_side_effects_in_loops,
            "max_node_executions": constraints.max_node_executions_cap,
            "max_total_runtime_s": 120,
        },
        "inputs": inputs,
        "nodes": [
            {"id": "load_prev", "type": "tool", "assigned_entity": "state_store", "depends_on": [],
             "inputs": {"op": "load_json", "path": "$graph.inputs.state_path"},
             "outputs": {"result": {}}, "policy": {"effect_class": "read", "timeout_s": 10}},
            {"id": "fetch", "type": "tool", "assigned_entity": "web_search", "depends_on": [],
             "inputs": {"companies": "$graph.inputs.companies", "recency_days": "$graph.inputs.recency_days"},
             "outputs": {"result": {}}, "policy": {"effect_class": "read", "timeout_s": 30}},
            {"id": "normalize", "type": "transform", "assigned_entity": "transformer", "depends_on": ["fetch"],
             "inputs": {"raw": "$node.fetch.result"}, "outputs": {"result": {}}},
            {"id": "score", "type": "eval", "assigned_entity": "evaluator", "depends_on": ["normalize"],
             "inputs": {"expression": "$node.normalize.result", "outputs": ["scored"]}, "outputs": {"scored": {}}},
            {"id": "diff", "type": "transform", "assigned_entity": "transformer", "depends_on": ["load_prev", "score"],
             "inputs": {"prev": "$node.load_prev.result", "cur": "$node.score.scored"}, "outputs": {"result": {}}},
            {"id": "write_report", "type": "tool", "assigned_entity": "file_writer", "depends_on": ["diff"],
             "inputs": {"path": "./.job_state/weekly_report.md", "content": "$node.diff.result"},
             "outputs": {"result": {}}, "checkpoints": {"before": True, "after": True},
             "policy": {"effect_class": "write", "max_retries": 0, "timeout_s": 10,
                       "idempotency_key": "weekly_report:$graph.inputs.state_path"}},
        ],
    }


def template_research_summary(goal: str, context: Dict[str, Any], constraints: Any) -> Dict[str, Any]:
    inputs = _research_inputs(goal, context)
    return {
        "graph_id": "planned_research_summary_v1",
        "version": "1.0",
        "run_policy": {
            "max_concurrency": 1,
            "failure_mode": constraints.failure_mode,
            "max_total_runtime_s": 120,
            "max_node_executions": constraints.max_node_executions_cap,
        },
        "inputs": inputs,
        "nodes": [
            {"id": "normalize", "type": "transform", "assigned_entity": "transformer", "depends_on": [],
             "inputs": {"topic": "$graph.inputs.topic"}, "outputs": {"result": {}}},
            {"id": "fetch_refs", "type": "tool", "assigned_entity": "web_search", "depends_on": ["normalize"],
             "inputs": {
                 "query": "$graph.inputs.query",
                 "query_variants": "$graph.inputs.query_variants",
                 "kind": "$graph.inputs.kind",
                 "freshness": "$graph.inputs.freshness",
                 "result_window": "$graph.inputs.result_window",
             }, "outputs": {"result": {}},
             "policy": {"effect_class": "read", "timeout_s": 30}},
            {"id": "summarize", "type": "agent", "assigned_entity": "summarizer_agent", "depends_on": ["fetch_refs"],
             "inputs": {
                 "docs": "$node.fetch_refs.result",
                 "answer_style": "$graph.inputs.answer_style",
                 "fetch_page_count": "$graph.inputs.fetch_page_count",
             }, "outputs": {"result": {}},
             "checkpoints": {"before": True, "after": True}, "policy": {"timeout_s": 60}},
            {"id": "eval_quality", "type": "eval", "assigned_entity": "evaluator", "depends_on": ["summarize"],
             "inputs": {"expression": "$node.summarize.result", "outputs": ["score"]}, "outputs": {"score": {}}},
        ],
    }


def template_generic_workflow(goal: str, context: Dict[str, Any], constraints: Any) -> Dict[str, Any]:
    return {
        "graph_id": "planned_generic_workflow_v1",
        "version": "1.0",
        "run_policy": {
            "max_concurrency": 1,
            "failure_mode": constraints.failure_mode,
            "max_node_executions": constraints.max_node_executions_cap,
        },
        "inputs": context.get("inputs", {"goal": goal}),
        "nodes": [
            {"id": "analyze", "type": "agent", "assigned_entity": "worker_agent", "depends_on": [],
             "inputs": {"goal": "$graph.inputs.goal"}, "outputs": {"result": {}},
             "checkpoints": {"before": True, "after": True}, "policy": {"timeout_s": 60}},
            {"id": "eval", "type": "eval", "assigned_entity": "evaluator", "depends_on": ["analyze"],
             "inputs": {"expression": "$node.analyze.result", "outputs": ["score"]}, "outputs": {"score": {}}},
        ],
    }


def template_fourclaw_single_post(goal: str, context: Dict[str, Any], constraints: Any) -> Dict[str, Any]:
    """Single agent node: fourclaw-auto-post with graph input 'goal' as mandatory topic."""
    return {
        "graph_id": "fourclaw_single_post_v1",
        "version": "1.0",
        "run_policy": {
            "max_concurrency": 1,
            "failure_mode": constraints.failure_mode,
            "max_node_executions": constraints.max_node_executions_cap,
            "strict_bindings": False,
        },
        "inputs": {"goal": goal},
        "nodes": [
            {
                "id": "post",
                "type": "agent",
                "assigned_entity": "fourclaw-auto-post",
                "depends_on": [],
                "inputs": {"goal": "$graph.inputs.goal"},
                "outputs": {"result": {}},
                "checkpoints": {"before": True, "after": True},
                "policy": {"timeout_s": 300, "max_retries": 0},
            },
        ],
    }


TEMPLATES = {
    "document_review_fanout": template_document_review_fanout,
    "job_search_weekly_diff": template_job_search_weekly_diff,
    "research_summary": template_research_summary,
    "generic_workflow": template_generic_workflow,
    "fourclaw_single_post": template_fourclaw_single_post,
}
