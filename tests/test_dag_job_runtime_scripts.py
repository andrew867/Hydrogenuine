#!/usr/bin/env python3
import json
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dag_runtime_jobs as registry
import prepare_dag_runtime_jobs as patcher
import run_dag_job as launcher


def _make_workspace() -> Path:
    root = Path.cwd() / ".tmp_dag_runtime_tests"
    root.mkdir(parents=True, exist_ok=True)
    ws = root / f"ws_{uuid.uuid4().hex}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def test_patch_message_uses_runtime_launcher_command():
    data = {
        "jobs": [
            {"id": "fourclaw-engage", "payload": {"kind": "agentTurn", "message": "old"}},
        ]
    }
    changed, missing = patcher._patch_jobs(data)
    assert changed == ["fourclaw-engage"]
    assert "fourclaw-engage" not in missing
    msg = data["jobs"][0]["payload"]["message"]
    assert "python scripts/run_dag_job.py --job-id fourclaw-engage" in msg
    assert "WAVE" not in msg
    assert "cutover" not in msg.lower()


def test_runtime_registry_covers_expected_production_jobs():
    required = {
        "fourclaw-auto-post-cadence",
        "fourclaw-engage",
        "moltbook-auto-post",
        "moltbook-engage",
        "aichan-auto-post",
        "aichan-engage",
        "agentchan-auto-post",
        "agentchan-engage",
        "rcmp-job-search-monitor",
        "knowledge-research-auto",
        "overseer-monitor",
        "moltstack-draft",
        "moltstack-publish",
        "memory-maintenance",
    }
    assert required.issubset(set(registry.DAG_JOB_REGISTRY.keys()))


def test_launcher_builds_hg_command():
    workspace = Path.cwd()
    run_dir = workspace / "memory" / "automation" / "dag_runs" / "x" / "run_test"
    cmd = launcher._build_command(
        workspace=workspace,
        dag_path="memory/automation/dags/fourclaw_engage.json",
        inputs=("goal=test",),
        run_dir=run_dir,
        prefer_cli=True,
    )
    assert cmd[0] == "hg-run-dag"
    assert "memory/automation/dags/fourclaw_engage.json" in cmd
    assert "--run-dir" in cmd
    assert str(run_dir) in cmd


def test_launcher_artifact_check():
    ws = _make_workspace()
    try:
        run_dir = ws / "memory" / "automation" / "dag_runs" / "job" / "run_1"
        run_dir.mkdir(parents=True, exist_ok=True)
        ok, missing = launcher._artifacts_ok(run_dir)
        assert ok is False
        assert "summary.json" in ",".join(missing)
        (run_dir / "summary.json").write_text("{}", encoding="utf-8")
        (run_dir / "events.jsonl").write_text("", encoding="utf-8")
        ok2, missing2 = launcher._artifacts_ok(run_dir)
        assert ok2 is True
        assert missing2 == []
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_runtime_config_from_jobs_message_detection(tmp_path):
    jobs = {
        "version": 1,
        "jobs": [
            {
                "id": "fourclaw-engage",
                "payload": {
                    "kind": "agentTurn",
                    "message": "python scripts/run_dag_job.py --job-id fourclaw-engage",
                },
            }
        ],
    }
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps(jobs), encoding="utf-8")
    cfg = patcher._load_jobs(path)
    assert cfg["jobs"][0]["id"] == "fourclaw-engage"
