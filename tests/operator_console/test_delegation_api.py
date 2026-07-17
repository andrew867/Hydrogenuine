"""Tests for delegation API: summary, anomalies, and incident report."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def test_incident_report_contains_anomalies_and_intervention(tmp_path):
    """Incident report export contains anomalies and interventions for a run."""
    run_id = "test-run-123"
    (tmp_path / "delegation_summary.json").write_text(
        json.dumps({
            "run_id": run_id,
            "workflow_id": "w1",
            "metrics": {"delegation_depth_max": 1, "total_work_items": 3},
            "anomalies": [
                {"detector_id": "D1_runaway_delegation", "severity": "warn", "recommended_action": "constrain", "evidence": [{"pointer": "depth", "value": 14}]}
            ],
            "quality": {"score": 0.8, "degraded": False},
            "intervention": {"step": "warn", "exceeded_budget": None, "recorded": True},
            "final_state": {"status": "success", "external_writes_attempted": "no", "external_writes_blocked": "no"},
            "top_bottlenecks": [],
        }),
        encoding="utf-8",
    )
    from operator_console.server.app.services import incident_report
    with patch("operator_console.server.app.services.incident_report.get_run", lambda rid: {"run_id": run_id, "run_dir": str(tmp_path)} if rid == run_id else None):
        res = incident_report.generate_incident_report(run_id)
    assert res.get("ok") is True
    report = res.get("report", {})
    assert "anomalies" in report
    assert len(report["anomalies"]) >= 1
    assert report["anomalies"][0].get("detector_id") == "D1_runaway_delegation"
    assert "intervention" in report
    assert report["intervention"].get("step") in ("warn", "slowdown", "constrain", "sandbox", "escalate", "halt")


def test_incident_report_md_includes_anomalies_and_intervention(tmp_path):
    """Incident report Markdown includes anomalies and intervention sections."""
    run_id = "test-run-md"
    (tmp_path / "delegation_summary.json").write_text(
        json.dumps({
            "run_id": run_id,
            "workflow_id": "w1",
            "metrics": {},
            "anomalies": [{"detector_id": "D3_looping_thrash", "severity": "warn", "recommended_action": "breaker", "evidence": []}],
            "quality": {},
            "intervention": {"step": "warn"},
            "final_state": {},
            "top_bottlenecks": [],
        }),
        encoding="utf-8",
    )
    from operator_console.server.app.services import incident_report
    with patch("operator_console.server.app.services.incident_report.get_run", lambda rid: {"run_id": run_id, "run_dir": str(tmp_path)} if rid == run_id else None):
        md = incident_report.incident_report_md(run_id)
    assert "Anomalies" in md
    assert "Intervention" in md
    assert "D3_looping_thrash" in md
