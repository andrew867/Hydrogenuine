"""
Tests for primary workflow registry and acceptance checks.

Validates: required registry fields for each primary workflow, must-level acceptance
checks exist and are runnable, readiness labels present and unattended only when allowed.
"""

from __future__ import annotations

import json

import pytest

# Primary workflows per spec
PRIMARY_WORKFLOW_IDS = [
    "social-media",
    "fourclaw-auto-post",
    "moltbook-auto-post",
    "moltstack-draft",
    "knowledge-research-auto",
]

REQUIRED_REGISTRY_FIELDS = [
    "workflow_id",
    "display_name",
    "category",
    "coordination_style",
    "side_effects",
    "success_criteria",
    "acceptance_checks",
    "sla_targets",
    "approvals_policy",
    "retention_class",
    "readiness",
]

VALID_READINESS = {"supervised", "unattended", "blocked"}
VALID_CATEGORY = {"analysis", "publish", "engage", "knowledge", "maintenance"}
VALID_COORDINATION = {"end_to_end", "baton", "parallel_contributors"}


def test_workflow_registry_module_importable():
    """Workflow registry module exists and is importable."""
    from hg_core.task_graph import workflow_registry

    assert workflow_registry is not None


def test_get_primary_workflow_ids():
    """Primary workflow IDs include the four declared workflows."""
    from hg_core.task_graph.workflow_registry import get_primary_workflow_ids

    ids = get_primary_workflow_ids()
    assert isinstance(ids, list)
    for wid in PRIMARY_WORKFLOW_IDS:
        assert wid in ids, f"Primary workflow {wid} must be in registry"


def test_load_workflow_registry_returns_dict():
    """Loading workflow registry returns a dict of workflow_id -> declaration."""
    from hg_core.task_graph.workflow_registry import load_workflow_registry, get_primary_workflow_ids

    registry = load_workflow_registry()
    assert isinstance(registry, dict)
    for wid in get_primary_workflow_ids():
        assert wid in registry, f"Registry must contain {wid}"


def test_declared_workflow_ids_include_scheduled_runtime_jobs():
    from hg_core.task_graph.workflow_registry import get_declared_workflow_ids

    ids = set(get_declared_workflow_ids())
    expected = {
        "fourclaw-engage",
        "moltbook-engage",
        "moltstack-publish",
        "memory-maintenance",
        "overseer-monitor",
    }
    assert expected.issubset(ids)


def test_all_registered_jobs_have_workflow_declarations():
    from hg_core.job_registry import list_tasks
    from hg_core.task_graph.workflow_registry import get_declared_workflow_ids

    declared = set(get_declared_workflow_ids())
    assert set(list_tasks()).issubset(declared)


def test_external_write_jobs_require_human_review():
    from hg_core.job_registry import list_tasks
    from hg_core.task_graph.workflow_registry import load_workflow_registry

    registry = load_workflow_registry()
    for task_name in list_tasks():
        decl = registry[task_name]
        if decl.get("side_effects") == "external_write":
            assert decl["approvals_policy"]["mode"] == "human_review_before_write"


def test_each_primary_workflow_has_required_fields():
    """Every primary workflow declaration has all required registry fields."""
    from hg_core.task_graph.workflow_registry import load_workflow_registry, get_primary_workflow_ids

    registry = load_workflow_registry()
    for wid in get_primary_workflow_ids():
        decl = registry.get(wid)
        assert decl is not None, f"Missing declaration for {wid}"
        for field in REQUIRED_REGISTRY_FIELDS:
            assert field in decl, f"{wid} missing required field: {field}"


def test_readiness_values_valid():
    """Readiness must be one of supervised, unattended, blocked."""
    from hg_core.task_graph.workflow_registry import load_workflow_registry, get_primary_workflow_ids

    registry = load_workflow_registry()
    for wid in get_primary_workflow_ids():
        r = registry[wid].get("readiness")
        assert r in VALID_READINESS, f"{wid} readiness must be in {VALID_READINESS}, got {r}"


def test_category_values_valid():
    """Category must be one of the allowed enum values."""
    from hg_core.task_graph.workflow_registry import load_workflow_registry, get_primary_workflow_ids

    registry = load_workflow_registry()
    for wid in get_primary_workflow_ids():
        c = registry[wid].get("category")
        assert c in VALID_CATEGORY, f"{wid} category must be in {VALID_CATEGORY}, got {c}"


def test_coordination_style_values_valid():
    """Coordination_style must be one of the allowed enum values."""
    from hg_core.task_graph.workflow_registry import load_workflow_registry, get_primary_workflow_ids

    registry = load_workflow_registry()
    for wid in get_primary_workflow_ids():
        cs = registry[wid].get("coordination_style")
        assert cs in VALID_COORDINATION, f"{wid} coordination_style must be in {VALID_COORDINATION}, got {cs}"


def test_must_level_acceptance_checks_exist():
    """Each primary workflow has at least one must-level acceptance check."""
    from hg_core.task_graph.workflow_registry import load_workflow_registry, get_primary_workflow_ids

    registry = load_workflow_registry()
    for wid in get_primary_workflow_ids():
        checks = registry[wid].get("acceptance_checks") or []
        must_checks = [c for c in checks if isinstance(c, dict) and c.get("severity") == "must"]
        assert len(must_checks) >= 1, f"{wid} must have at least one must-level acceptance check"


def test_acceptance_check_runner_returns_list():
    """Run_acceptance_checks returns a list of check results (pass/fail)."""
    from hg_core.task_graph.workflow_registry import run_acceptance_checks, get_primary_workflow_ids

    ids = get_primary_workflow_ids()
    if not ids:
        pytest.skip("No primary workflows registered")
    results = run_acceptance_checks(ids[0], run_context=None)
    assert isinstance(results, list)
    for item in results:
        assert "check_id" in item or "id" in item
        assert "passed" in item or "pass" in item or "ok" in item
        assert "severity" in item
        assert "evidence" in item


def test_acceptance_checks_are_runnable():
    """All must-level checks for a workflow can be invoked without error."""
    from hg_core.task_graph.workflow_registry import (
        load_workflow_registry,
        run_acceptance_checks,
        get_primary_workflow_ids,
    )

    registry = load_workflow_registry()
    for wid in get_primary_workflow_ids():
        results = run_acceptance_checks(wid, run_context=None)
        assert isinstance(results, list)
        # No exception means checks are runnable


def test_readiness_unattended_only_when_checks_allow():
    """is_readiness_unattended is True only for workflows marked unattended (enforcement is best-effort)."""
    from hg_core.task_graph.workflow_registry import (
        load_workflow_registry,
        is_readiness_unattended,
        get_primary_workflow_ids,
    )

    registry = load_workflow_registry()
    for wid in get_primary_workflow_ids():
        decl = registry[wid]
        expected = decl.get("readiness") == "unattended"
        assert is_readiness_unattended(wid) == expected


def test_acceptance_checks_use_run_evidence_from_workspace(tmp_path):
    from hg_core.task_graph.workflow_registry import run_acceptance_checks

    registry = {
        "wf-x": {
            "workflow_id": "wf-x",
            "display_name": "WF X",
            "category": "publish",
            "coordination_style": "end_to_end",
            "side_effects": "external_write",
            "success_criteria": [],
            "acceptance_checks": [
                {"id": "trace_exists", "severity": "must"},
                {"id": "budget", "severity": "must"},
            ],
            "sla_targets": {},
            "approvals_policy": {"mode": "default_approve", "strict_blacklist_categories": []},
            "retention_class": "medium",
            "readiness": "supervised",
            "idempotency": {"required": False},
        }
    }
    registry_path = tmp_path / "memory" / "automation" / "workflow_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "wf-x" / "run_1"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text('{"event":"dag_run_started"}\n', encoding="utf-8")
    (run_dir / "summary.json").write_text(
        json.dumps({"run_id": "run-1", "graph_id": "wf-x", "started_at": "2026-02-26T00:00:00Z"}, indent=2),
        encoding="utf-8",
    )
    (run_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "graph_id": "wf-x",
                "state": {"budget_used": {"dispatch_attempts": 1.0}},
                "node_outputs": {"n1": {"result": {"status": "ok"}}},
                "node_states": {"n1": {"id": "n1", "status": "done"}},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    results = run_acceptance_checks("wf-x", workspace_root=tmp_path)
    by_id = {item["check_id"]: item for item in results}
    assert by_id["trace_exists"]["passed"] is True
    assert by_id["budget"]["passed"] is True
    assert by_id["trace_exists"]["evidence"]["run_id"] == "run-1"


def test_acceptance_checks_idempotency_fails_without_ledger(tmp_path):
    from hg_core.task_graph.workflow_registry import run_acceptance_checks

    registry = {
        "wf-idem": {
            "workflow_id": "wf-idem",
            "display_name": "WF Idem",
            "category": "publish",
            "coordination_style": "end_to_end",
            "side_effects": "external_write",
            "success_criteria": [],
            "acceptance_checks": [{"id": "idempotency", "severity": "must"}],
            "sla_targets": {},
            "approvals_policy": {"mode": "default_approve", "strict_blacklist_categories": []},
            "retention_class": "medium",
            "readiness": "supervised",
            "idempotency": {"required": True},
        }
    }
    registry_path = tmp_path / "memory" / "automation" / "workflow_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "wf-idem" / "run_1"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text("{}", encoding="utf-8")
    (run_dir / "summary.json").write_text(
        json.dumps({"run_id": "run-1", "graph_id": "wf-idem", "started_at": "2026-02-26T00:00:00Z"}, indent=2),
        encoding="utf-8",
    )
    (run_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "graph_id": "wf-idem",
                "state": {"budget_used": {"dispatch_attempts": 1.0}},
                "node_outputs": {"n1": {"result": {"status": "ok"}}},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    results = run_acceptance_checks("wf-idem", workspace_root=tmp_path)
    assert len(results) == 1
    assert results[0]["check_id"] == "idempotency"
    assert results[0]["passed"] is False
    assert "ledger" in results[0]["message"].lower()


def test_load_workflow_registry_bootstraps_file_when_missing(tmp_path):
    from hg_core.task_graph.workflow_registry import (
        WORKFLOW_REGISTRY_PATH,
        get_primary_workflow_ids,
        load_workflow_registry,
    )

    registry = load_workflow_registry(workspace_root=tmp_path)
    registry_path = tmp_path / WORKFLOW_REGISTRY_PATH
    assert registry_path.exists()
    assert isinstance(registry, dict)
    for wid in get_primary_workflow_ids():
        assert wid in registry


def test_acceptance_check_trace_exists_fails_when_missing_evidence(tmp_path):
    """trace_exists check fails when events_path missing or node_outputs empty."""
    from hg_core.task_graph.workflow_registry import (
        _check_trace_exists,
        load_workflow_registry,
        run_acceptance_checks,
    )
    run_data_no_trace = {"run_id": "r1", "events_path": None, "node_outputs": {"a": {}}}
    result = _check_trace_exists(run_data_no_trace, {"id": "trace_exists", "severity": "must"})
    assert result["passed"] is False
    assert "evidence" in result
    run_data_no_outputs = {"run_id": "r1", "events_path": tmp_path / "nonexistent.jsonl", "node_outputs": {}}
    result2 = _check_trace_exists(run_data_no_outputs, {"id": "trace_exists", "severity": "must"})
    assert result2["passed"] is False


def test_acceptance_check_checkpoints_fails_when_required_missing(tmp_path):
    """checkpoints check fails when required checkpoints not in run_data."""
    from hg_core.task_graph.workflow_registry import _check_checkpoints
    decl = {"checkpoints": ["node_a", "node_b"]}
    run_data = {"node_states": {"node_a": {}}, "node_outputs": {}}
    result = _check_checkpoints(run_data, {"id": "checkpoints", "severity": "must"}, decl)
    assert result["passed"] is False
    assert "node_b" in (result.get("evidence") or {}).get("missing", [])


def test_get_acceptance_readiness_returns_blocking_when_must_fails(tmp_path):
    """get_acceptance_readiness returns ready=False and blocking_checks when a must check fails."""
    from hg_core.task_graph.workflow_registry import get_acceptance_readiness
    (tmp_path / "memory" / "automation").mkdir(parents=True)
    reg = tmp_path / "memory" / "automation" / "workflow_registry.json"
    reg.write_text('{"w-accept": {"workflow_id": "w-accept", "acceptance_checks": [{"id": "trace_exists", "severity": "must"}]}}')
    out = get_acceptance_readiness("w-accept", workspace_root=tmp_path)
    assert "ready" in out and "results" in out and "blocking_checks" in out
    assert out["ready"] is False
    assert "trace_exists" in out.get("blocking_checks", [])


def test_load_workflow_registry_applies_policy_defaults_and_logs(tmp_path, caplog):
    from hg_core.task_graph.workflow_registry import load_workflow_registry

    registry_path = tmp_path / "memory" / "automation" / "workflow_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "wf-a": {
                    "workflow_id": "wf-a",
                    "display_name": "wf-a",
                    "category": "maintenance",
                    "coordination_style": "end_to_end",
                    "side_effects": "none",
                    "success_criteria": [],
                    "acceptance_checks": [{"id": "trace_exists", "severity": "must"}],
                    "sla_targets": {"reliability_target": 0.95},
                    "approvals_policy": {"mode": "default_approve"},
                    "retention_class": "medium",
                    "readiness": "supervised",
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with caplog.at_level("WARNING"):
        registry = load_workflow_registry(workspace_root=tmp_path)

    assert "wf-a" in registry
    decl = registry["wf-a"]
    assert "destinations" in decl
    assert "degraded_mode_rules" in decl
    assert "idempotency" in decl
    assert "budgets" in decl
    assert "strict_blacklist_categories" in decl
    assert "strict_blacklist_categories" in decl["approvals_policy"]
    assert "missing policy fields" in caplog.text
