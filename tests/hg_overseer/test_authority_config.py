"""Tests for authority config and TaskFileEditor (authority_actions_contract)."""

import json
import pytest
from pathlib import Path

from hg_overseer.overseer_core.overseer_main import load_authority_config
from hg_overseer.overseer_core.task_file_editor import TaskFileEditor


def test_load_authority_config_missing_returns_default(tmp_path):
    """load_authority_config returns default when path does not exist."""
    missing = tmp_path / "nonexistent.json"
    cfg = load_authority_config(missing)
    assert cfg == {"mode": "moderate", "thresholds": {}}
    assert "mode" in cfg
    assert "thresholds" in cfg


def test_load_authority_config_valid_json(tmp_path):
    """load_authority_config parses valid JSON and returns dict with mode, thresholds, task_file_editing."""
    config_path = tmp_path / "authority-config.json"
    config_path.write_text(
        json.dumps({
            "mode": "strict",
            "thresholds": {"max_error_rate": 0.1},
            "task_file_editing_enabled": True,
            "task_file_editing": {"max_edits_per_cycle": 5},
        }),
        encoding="utf-8",
    )
    cfg = load_authority_config(config_path)
    assert cfg["mode"] == "strict"
    assert cfg["thresholds"] == {"max_error_rate": 0.1}
    assert cfg.get("task_file_editing_enabled") is True
    assert cfg.get("task_file_editing", {}).get("max_edits_per_cycle") == 5


def test_load_authority_config_malformed_returns_default(tmp_path):
    """load_authority_config returns default when JSON is malformed."""
    config_path = tmp_path / "bad.json"
    config_path.write_text("{ invalid json }", encoding="utf-8")
    cfg = load_authority_config(config_path)
    assert cfg == {"mode": "moderate", "thresholds": {}}


def test_task_file_editor_scan_for_issues_nonexistent_returns_empty(tmp_path):
    """TaskFileEditor.scan_for_issues returns [] when file does not exist."""
    editor = TaskFileEditor(backup_dir=tmp_path / "backups")
    issues = editor.scan_for_issues(tmp_path / "nonexistent.md", [])
    assert issues == []


def test_task_file_editor_scan_for_issues_returns_expected_shape(tmp_path):
    """TaskFileEditor.scan_for_issues returns list of dicts with type, severity, description, suggested_fix, auto_fixable."""
    task_file = tmp_path / "task.md"
    task_file.write_text("# Task\n\nUse `command1 && command2` here.\n", encoding="utf-8")
    editor = TaskFileEditor(backup_dir=tmp_path / "backups")
    issues = editor.scan_for_issues(task_file, [])
    assert isinstance(issues, list)
    assert len(issues) >= 1
    for issue in issues:
        assert "type" in issue
        assert "severity" in issue
        assert "description" in issue
        assert "suggested_fix" in issue
        assert "auto_fixable" in issue


def test_task_file_editor_apply_fix_returns_report_shape(tmp_path):
    """TaskFileEditor.apply_fix returns report with file, issue_type, applied, backup_path, changes_made, error."""
    task_file = tmp_path / "task.md"
    task_file.write_text("# Task\n\nUse `command1 && command2` here.\n", encoding="utf-8")
    editor = TaskFileEditor(backup_dir=tmp_path / "backups")
    issues = editor.scan_for_issues(task_file, [])
    assert len(issues) >= 1
    issue = issues[0]
    report = editor.apply_fix(task_file, issue)
    assert "file" in report
    assert "issue_type" in report
    assert "applied" in report
    assert "backup_path" in report
    assert "changes_made" in report
    assert "error" in report
    assert isinstance(report["changes_made"], list)


def test_task_file_editor_apply_fix_respects_max_edits_caller(tmp_path):
    """Caller enforces max_edits_per_cycle; apply_fix itself does not cap (contract: caps in overseer_main)."""
    task_file = tmp_path / "task.md"
    task_file.write_text("# Task\n\nContent.\n", encoding="utf-8")
    editor = TaskFileEditor(backup_dir=tmp_path / "backups")
    # apply_fix with non-auto-fixable or unknown type returns report with applied=False
    report = editor.apply_fix(task_file, {"type": "unknown_type", "severity": "high"})
    assert report.get("applied") is False
    assert "error" in report
