"""Phase 10: All DAG jobs as working task templates; run_dag_job --job-id dry-run and run dir created."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts"


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _get_registry():
    sys.path.insert(0, str(_scripts_dir()))
    try:
        from dag_runtime_jobs import DAG_JOB_REGISTRY
        return DAG_JOB_REGISTRY
    finally:
        if str(_scripts_dir()) in sys.path:
            sys.path.remove(str(_scripts_dir()))


@pytest.fixture(scope="module")
def registry():
    return _get_registry()


def test_every_job_dag_file_exists(registry):
    """For every job_id in DAG_JOB_REGISTRY, the DAG file exists."""
    workspace = _workspace_root()
    for job_id, job in registry.items():
        dag_path = workspace / getattr(job, "dag_path", "")
        assert dag_path.exists(), f"job_id={job_id} dag_path={dag_path} missing"


def test_every_job_dry_run_exit_0(registry):
    """For every job_id, run_dag_job --job-id X --dry-run exits 0."""
    workspace = _workspace_root()
    run_dag_job = workspace / "scripts" / "run_dag_job.py"
    if not run_dag_job.exists():
        pytest.skip("scripts/run_dag_job.py not found")
    for job_id in registry:
        proc = subprocess.run(
            [sys.executable, str(run_dag_job), "--job-id", job_id, "--workspace", str(workspace), "--dry-run"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0, f"job_id={job_id} dry-run failed: {proc.stderr!r}"
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
        assert out.get("ok") is True or out.get("dry_run") is True, f"job_id={job_id} output: {out}"


def test_phase10_smoke_run_exit_0_and_run_dir_created(registry):
    """run_dag_job --job-id phase10-smoke (linear_three_steps) exits 0 and run_dir is created."""
    if "phase10-smoke" not in registry:
        pytest.skip("phase10-smoke not in DAG_JOB_REGISTRY")
    workspace = _workspace_root()
    run_dag_job = workspace / "scripts" / "run_dag_job.py"
    if not run_dag_job.exists():
        pytest.skip("scripts/run_dag_job.py not found")
    proc = subprocess.run(
        [sys.executable, str(run_dag_job), "--job-id", "phase10-smoke", "--workspace", str(workspace)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    assert proc.returncode == 0, f"phase10-smoke failed: returncode={proc.returncode} stderr={proc.stderr} out={out}"
    run_dir_str = out.get("run_dir", "")
    assert run_dir_str, "run_dir missing in output"
    run_dir = Path(run_dir_str)
    assert run_dir.is_dir(), f"run_dir not created: {run_dir}"
    assert (run_dir / "summary.json").exists() or (run_dir / "state.json").exists(), "no summary or state in run_dir"


def test_moltstack_draft_dry_run_exit_0(registry):
    """run_dag_job --job-id moltstack-draft --dry-run exits 0 (Phase 10 style)."""
    if "moltstack-draft" not in registry:
        pytest.skip("moltstack-draft not in DAG_JOB_REGISTRY")
    workspace = _workspace_root()
    run_dag_job = workspace / "scripts" / "run_dag_job.py"
    if not run_dag_job.exists():
        pytest.skip("scripts/run_dag_job.py not found")
    proc = subprocess.run(
        [sys.executable, str(run_dag_job), "--job-id", "moltstack-draft", "--workspace", str(workspace), "--dry-run"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, f"moltstack-draft dry-run failed: {proc.stderr!r}"
    out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    assert out.get("ok") is True or out.get("dry_run") is True, f"moltstack-draft output: {out}"


def test_moltstack_publish_dry_run_exit_0(registry):
    """run_dag_job --job-id moltstack-publish --dry-run exits 0 (Phase 10 style)."""
    if "moltstack-publish" not in registry:
        pytest.skip("moltstack-publish not in DAG_JOB_REGISTRY")
    workspace = _workspace_root()
    run_dag_job = workspace / "scripts" / "run_dag_job.py"
    if not run_dag_job.exists():
        pytest.skip("scripts/run_dag_job.py not found")
    proc = subprocess.run(
        [sys.executable, str(run_dag_job), "--job-id", "moltstack-publish", "--workspace", str(workspace), "--dry-run"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, f"moltstack-publish dry-run failed: {proc.stderr!r}"
    out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    assert out.get("ok") is True or out.get("dry_run") is True, f"moltstack-publish output: {out}"
