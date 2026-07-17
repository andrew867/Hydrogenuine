from pathlib import Path

from hg_core.run_automation_task import execute_task_directly, find_cron_job_id


def test_find_cron_job_id_routes_social_tasks_to_unified_social_media():
    assert find_cron_job_id("moltbook-engage") == "social-media"
    assert find_cron_job_id("fourclaw-auto-post") == "social-media"
    assert find_cron_job_id("agentchan-auto-post") == "social-media"
    assert find_cron_job_id("social-media") == "social-media"
    assert find_cron_job_id("overseer-monitor") == "overseer-monitor"


def test_execute_task_directly_returns_native_runtime_contract(monkeypatch, tmp_path):
    tasks_dir = tmp_path / "skills" / "automation" / "tasks"
    tasks_dir.mkdir(parents=True)
    task_file = tasks_dir / "moltbook-engage.md"
    task_file.write_text("# task\n", encoding="utf-8")

    monkeypatch.setattr("hg_core.run_automation_task.get_task_file_path", lambda name: task_file)
    monkeypatch.setattr("hg_core.run_automation_task.resolve_task_file_name", lambda name: "moltbook-engage")

    result = execute_task_directly("moltbook-engage")

    assert result["ok"] is True
    assert result["action"] == "native_runtime_execution"
    assert result["execution_mode"] == "native_runtime_contract"
    assert result["instruction_request_tool"] == "lifecycle.get_runtime_contract"
    assert result["notify_tool"] == "lifecycle.notify_human"
    assert result["sleep_tool"] == "lifecycle.request_sleep"
    assert result["session_target"] == "automation-moltbook-engage"
    assert "Read skills/automation/tasks" not in result["message"]
    assert "Request compact execution guidance through lifecycle.get_runtime_contract." in result["instructions"]


def test_execute_task_directly_reports_held_agency_control(monkeypatch, tmp_path):
    tasks_dir = tmp_path / "skills" / "automation" / "tasks"
    tasks_dir.mkdir(parents=True)
    task_file = tasks_dir / "fourclaw-auto-post.md"
    task_file.write_text("# task\n", encoding="utf-8")
    operational_dir = tmp_path / "memory" / "automation" / "automation-underling-chan"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"held","reason":"quiet hours","updated_by":"operator"}',
        encoding="utf-8",
    )

    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setattr("hg_core.run_automation_task.get_task_file_path", lambda name: task_file)
    monkeypatch.setattr("hg_core.run_automation_task.resolve_task_file_name", lambda name: "fourclaw-auto-post")

    result = execute_task_directly("fourclaw-auto-post")

    assert result["ok"] is True
    assert result["agency_control_summary"]["effective_mode"] == "held"
    assert "currently held by persona-local agency control" in result["message"]
    assert "Agency control is held." in result["instructions"]


def test_execute_task_directly_reports_review_only_agency_control(monkeypatch, tmp_path):
    tasks_dir = tmp_path / "skills" / "automation" / "tasks"
    tasks_dir.mkdir(parents=True)
    task_file = tasks_dir / "fourclaw-auto-post.md"
    task_file.write_text("# task\n", encoding="utf-8")
    operational_dir = tmp_path / "memory" / "automation" / "automation-underling-chan"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"review_only","reason":"supervised rollout","updated_by":"operator"}',
        encoding="utf-8",
    )

    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setattr("hg_core.run_automation_task.get_task_file_path", lambda name: task_file)
    monkeypatch.setattr("hg_core.run_automation_task.resolve_task_file_name", lambda name: "fourclaw-auto-post")

    result = execute_task_directly("fourclaw-auto-post")

    assert result["ok"] is True
    assert result["agency_control_summary"]["effective_mode"] == "review_only"
    assert "currently in review-only mode" in result["message"]
    assert "Agency control is review-only." in result["instructions"]
