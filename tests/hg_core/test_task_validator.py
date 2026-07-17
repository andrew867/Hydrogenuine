"""
Tests for task file validator (required sections, PowerShell lint).
See docs/specs/task_file_spec.md.
"""

import pytest
from pathlib import Path

from hg_core.task_validator import (
    validate_task_file,
    validate_all_tasks,
    get_task_directory,
    LOAD_MEMORY_EXCEPTIONS,
    MINIMAL_TASKS,
)


def test_valid_task_passes(tmp_path):
    """Valid task with Mission, Load Session Memory, Execution Rules passes."""
    task = tmp_path / "valid-task.md"
    task.write_text("""# Valid Task

## Mission

Do something useful.

## Load Session Memory

Memory is loaded automatically.

## Execution Rules

Execute all steps.
""", encoding="utf-8")
    valid, errors, warnings = validate_task_file(task)
    assert valid is True
    assert not errors
    assert isinstance(warnings, list)


def test_missing_mission_fails(tmp_path):
    """Task missing Mission fails validation."""
    task = tmp_path / "no-mission.md"
    task.write_text("""# No Mission

## Load Session Memory

Memory here.

## Execution Rules

Rules here.
""", encoding="utf-8")
    valid, errors, warnings = validate_task_file(task)
    assert valid is False
    assert any("Mission" in e for e in errors)


def test_missing_load_memory_fails(tmp_path):
    """Task missing Load Memory fails unless exception."""
    task = tmp_path / "no-load-memory.md"
    task.write_text("""# Task

## Mission

Do it.

## Execution Rules

Rules.
""", encoding="utf-8")
    valid, errors, _ = validate_task_file(task, require_load_memory=True)
    assert valid is False
    assert any("Load" in e for e in errors)
    valid2, errors2, _ = validate_task_file(task, require_load_memory=False)
    assert valid2 is True
    assert not errors2


def test_missing_execution_fails(tmp_path):
    """Task missing Execution Rules/Steps fails."""
    task = tmp_path / "no-execution.md"
    task.write_text("""# Task

## Mission

Do it.

## Load Session Memory

Memory.
""", encoding="utf-8")
    valid, errors, _ = validate_task_file(task)
    assert valid is False
    assert any("Execution" in e for e in errors)


def test_powershell_lint_detects_unsafe_pattern(tmp_path):
    """Linter flags line with PowerShell and semicolon inside double-quoted string."""
    task = tmp_path / "powershell-unsafe.md"
    task.write_text("""# Task

## Mission

Run something.

## Load Session Memory

Memory.

## Execution Rules

Run: powershell -Command "Get-Date; Get-Host"
""", encoding="utf-8")
    valid, errors, warnings = validate_task_file(task)
    assert valid is True
    assert any("semicolon" in w.lower() or "powershell" in w.lower() for w in warnings)


def test_all_current_task_files_pass(workspace_root):
    """All task .md files in skills/automation/tasks/ pass validation (with exceptions)."""
    all_valid, results = validate_all_tasks(workspace_root)
    failures = [(p, e) for p, e, _ in results if e]
    assert all_valid, f"Task validation failed: {failures}"


@pytest.fixture
def workspace_root():
    """Workspace root (project root)."""
    return Path(__file__).resolve().parent.parent.parent
