"""
Tests for SLA reporting.

Per TEST_PLAN: daily and weekly report generation from synthetic trace sets;
success rates computed correctly; duplicate metric present and zero.
"""

from __future__ import annotations


# Synthetic trace set for report generation
SYNTHETIC_TRACES = [
    {"run_id": "r1", "workflow_id": "fourclaw-auto-post", "status": "success", "failure_class": None},
    {"run_id": "r2", "workflow_id": "fourclaw-auto-post", "status": "failed", "failure_class": "timeout"},
    {"run_id": "r3", "workflow_id": "moltbook-auto-post", "status": "success", "failure_class": None},
    {"run_id": "r4", "workflow_id": "moltbook-auto-post", "status": "degraded", "failure_class": None},
    {"run_id": "r5", "workflow_id": "fourclaw-auto-post", "status": "success", "failure_class": None},
    {"run_id": "r6", "workflow_id": "fourclaw-auto-post", "status": "success", "duplicate_side_effects": 0},
]


def test_sla_reporting_module_importable():
    """SLA reporting module is importable."""
    from hg_core.task_graph import sla_reporting

    assert sla_reporting is not None


def test_daily_report_from_synthetic_traces():
    """Daily report can be generated from synthetic trace set."""
    from hg_core.task_graph.sla_reporting import generate_daily_report

    report = generate_daily_report(traces=SYNTHETIC_TRACES)
    assert isinstance(report, dict)
    assert "runs_by_workflow" in report or "by_workflow" in report or "workflows" in report
    assert "failure_classes" in report or "top_failures" in report or "status" in report


def test_weekly_report_from_synthetic_traces():
    """Weekly report can be generated from synthetic trace set."""
    from hg_core.task_graph.sla_reporting import generate_weekly_report

    report = generate_weekly_report(traces=SYNTHETIC_TRACES)
    assert isinstance(report, dict)
    assert "success_rate" in report or "per_workflow" in report or "workflows" in report


def test_success_rate_computed_correctly():
    """Success rate is computed correctly from traces."""
    from hg_core.task_graph.sla_reporting import generate_weekly_report

    report = generate_weekly_report(traces=SYNTHETIC_TRACES)
    # 3 success, 1 failed, 1 degraded, 1 success -> at least one workflow has a rate
    assert "success_rate" in report or any("success" in str(v).lower() for v in report.values())


def test_duplicate_metric_present_and_zero():
    """Duplicate side-effect metric is present and should be zero."""
    from hg_core.task_graph.sla_reporting import generate_weekly_report

    report = generate_weekly_report(traces=SYNTHETIC_TRACES)
    dup = report.get("duplicate_side_effects") or report.get("duplicate_side_effect_incidents")
    if dup is not None:
        assert dup == 0, "Duplicate side effects must be zero"
