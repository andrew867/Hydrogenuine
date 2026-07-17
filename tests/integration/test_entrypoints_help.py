"""Test that CLI entry points accept --help and exit 0."""

import os
import subprocess
import sys
import json
from pathlib import Path


def _parse_first_json_object(text: str) -> dict:
    decoder = json.JSONDecoder()
    obj, _end = decoder.raw_decode(text.lstrip())
    return obj


def test_run_task_help():
    """python -m hg_core.run_task --help exits 0."""
    result = subprocess.run(
        [sys.executable, "-m", "hg_core.run_task", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_overseer_main_help():
    """python -m hg_overseer.main --help exits 0."""
    result = subprocess.run(
        [sys.executable, "-m", "hg_overseer.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_social_media_routes_to_platform_task(tmp_path):
    """social-media --platform moltbook --mode auto-post resolves to moltbook-auto-post."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True)
    (workspace / "skills" / "automation" / "tasks").mkdir(parents=True)
    (workspace / "skills" / "automation" / "tasks" / "moltbook-auto-post.md").write_text(
        "# Moltbook\n\n## Mission\n\nPost.\n", encoding="utf-8"
    )
    (workspace / "skills" / "automation" / "tasks" / "social-media.md").write_text(
        "# Social Media\n\nRouter task.", encoding="utf-8"
    )
    env = os.environ.copy()
    env["HG_WORKSPACE"] = str(workspace)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    env["HOME"] = str(fake_home)
    if sys.platform == "win32":
        env["USERPROFILE"] = str(fake_home)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hg_core.run_task",
            "social-media",
            "--platform",
            "moltbook",
            "--mode",
            "auto-post",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "moltbook-auto-post" in result.stdout


def test_social_media_auto_resolves_stale_task_without_platform_mode(tmp_path):
    """social-media without explicit platform/mode resolves through lifecycle.choose_social_work."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "memory" / "automation").mkdir(parents=True)
    (workspace / "skills" / "automation" / "tasks").mkdir(parents=True)
    (workspace / "skills" / "automation" / "tasks" / "social-media.md").write_text(
        "# Social Media\n\nRouter task.", encoding="utf-8"
    )
    for task_name in ("moltbook-engage", "fourclaw-engage", "aichan-engage", "agentchan-engage"):
        (workspace / "skills" / "automation" / "tasks" / f"{task_name}.md").write_text(
            f"# {task_name}\n\n## Mission\n\nRun {task_name}.\n", encoding="utf-8"
        )
    run_log = workspace / "memory" / "automation" / "run_summaries.jsonl"
    run_log.write_text(
        "\n".join(
            [
                '{"job_id":"moltbook-engage","session_target":"automation-moltbook","summary":"x","ts_ms":3000}',
                '{"job_id":"fourclaw-engage","session_target":"automation-fourclaw","summary":"x","ts_ms":2000}',
                '{"job_id":"agentchan-engage","session_target":"automation-agentchan","summary":"x","ts_ms":1000}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HG_WORKSPACE"] = str(workspace)
    env["HG_GOAL"] = "check replies and engage"
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    env["HOME"] = str(fake_home)
    if sys.platform == "win32":
        env["USERPROFILE"] = str(fake_home)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hg_core.run_task",
            "social-media",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "aichan-engage" in result.stdout or "agentchan-engage" in result.stdout


def test_social_media_runs_unified_dag_when_hg_use_task_dag_enabled(tmp_path):
    """social-media stays as social-media under HG_USE_TASK_DAG=1 and executes the unified DAG path."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "memory" / "automation" / "dags").mkdir(parents=True)
    (workspace / "memory" / "automation").mkdir(parents=True, exist_ok=True)
    (workspace / "skills" / "automation" / "tasks").mkdir(parents=True)

    source_root = Path.cwd()
    social_dag_src = source_root / "memory" / "automation" / "dags" / "social_media.json"
    dag_registry_src = source_root / "memory" / "automation" / "dag_registry.json"
    (workspace / "memory" / "automation" / "dags" / "social_media.json").write_text(
        social_dag_src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    registry = json.loads(dag_registry_src.read_text(encoding="utf-8"))
    registry["social-media"] = "memory/automation/dags/social_media.json"
    (workspace / "memory" / "automation" / "dag_registry.json").write_text(
        json.dumps(registry, indent=2),
        encoding="utf-8",
    )

    (workspace / "skills" / "automation" / "tasks" / "social-media.md").write_text(
        "# Social Media\n\nUnified task.\n", encoding="utf-8"
    )
    for task_name in ("moltbook-engage", "fourclaw-engage", "aichan-engage", "agentchan-engage"):
        (workspace / "skills" / "automation" / "tasks" / f"{task_name}.md").write_text(
            f"# {task_name}\n\n## Mission\n\nRun {task_name}.\n",
            encoding="utf-8",
        )

    run_log = workspace / "memory" / "automation" / "run_summaries.jsonl"
    run_log.write_text(
        "\n".join(
            [
                '{"job_id":"moltbook-engage","session_target":"automation-moltbook","summary":"x","ts_ms":4000}',
                '{"job_id":"fourclaw-engage","session_target":"automation-fourclaw","summary":"x","ts_ms":3000}',
                '{"job_id":"agentchan-engage","session_target":"automation-agentchan","summary":"x","ts_ms":2000}',
                '{"job_id":"aichan-engage","session_target":"automation-aichan","summary":"x","ts_ms":1000}'
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["HG_WORKSPACE"] = str(workspace)
    env["HG_GOAL"] = "check replies and engage"
    env["HG_USE_TASK_DAG"] = "1"
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    env["HOME"] = str(fake_home)
    if sys.platform == "win32":
        env["USERPROFILE"] = str(fake_home)

    result = subprocess.run(
        [sys.executable, "-m", "hg_core.run_task", "social-media"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = _parse_first_json_object(result.stdout)
    assert payload.get("ok") is True
    assert payload.get("graph_id") == "social_media_v1"


def test_tiered_context_loading(tmp_path):
    """run_task without --full-task returns tiered context (mission + task_path, not full instructions)."""
    import json

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True)
    (workspace / "memory" / "automation").mkdir(parents=True)
    (workspace / "skills" / "automation" / "tasks").mkdir(parents=True)
    task_content = "# Moltbook\n\n## Mission\n\nCreate one post per cycle.\n\n---\n\n## Full steps..."
    (workspace / "skills" / "automation" / "tasks" / "moltbook-auto-post.md").write_text(task_content, encoding="utf-8")
    # Create minimal automation dir for session
    (workspace / "memory" / "automation" / "automation-moltbook-auto-post").mkdir(parents=True)

    env = os.environ.copy()
    env["HG_WORKSPACE"] = str(workspace)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    env["HOME"] = str(fake_home)
    if sys.platform == "win32":
        env["USERPROFILE"] = str(fake_home)

    result = subprocess.run(
        [sys.executable, "-m", "hg_core.run_task", "moltbook-auto-post"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data.get("ok") is True
    assert "mission" in data
    assert "task_path" in data
    assert "skills/automation/tasks/moltbook-auto-post.md" in data["task_path"]
    assert "Create one post" in data["mission"] or "post" in data["mission"].lower()
