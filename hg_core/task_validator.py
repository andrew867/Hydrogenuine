"""
Task file validator: required H2 sections (Mission, Load Memory, Execution Rules/Steps)
and optional PowerShell lint. See docs/specs/task_file_spec.md.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

# Task names that may omit "Load Memory" / "Load Session Memory"
LOAD_MEMORY_EXCEPTIONS = {"overseer-monitor", "knowledge-research-auto", "social-media"}
# Task names that only require Mission (minimal/stub tasks)
MINIMAL_TASKS = {"social-media"}


def _h2_headings(content: str) -> List[str]:
    """Return list of H2 heading titles (normalized: strip, lower)."""
    headings: List[str] = []
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("## ") and not s.startswith("## #"):
            title = s[3:].strip()
            if title:
                headings.append(title.lower())
    return headings


def _has_mission(headings: List[str]) -> bool:
    return any(h == "mission" for h in headings)


def _has_load_memory(headings: List[str]) -> bool:
    return any(
        h.startswith("load session memory") or h.startswith("load memory")
        for h in headings
    )


def _has_execution(headings: List[str]) -> bool:
    return any(
        h.startswith("execution rules") or h.startswith("execution steps")
        for h in headings
    )


def _powershell_warnings(content: str) -> List[Tuple[int, str]]:
    """Return list of (1-based line number, message) for PowerShell lint warnings."""
    warnings: List[Tuple[int, str]] = []
    # Flag line if it contains "powershell" and a double-quoted string with semicolon inside
    pattern = re.compile(r'powershell.*"[^"]*;[^"]*"', re.IGNORECASE)
    for i, line in enumerate(content.splitlines(), start=1):
        if pattern.search(line):
            warnings.append((i, "PowerShell: semicolon inside double-quoted string (may need escaping)"))
    return warnings


def validate_task_file(
    path: Path,
    *,
    require_load_memory: bool = True,
    require_execution: bool = True,
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate a task markdown file.

    Args:
        path: Path to the .md file.
        require_load_memory: If False, do not require Load Memory section (for exceptions).
        require_execution: If False, do not require Execution Rules/Steps (for minimal tasks).

    Returns:
        (valid, errors, warnings). valid is False if any required section is missing.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not path.exists():
        return False, [f"File not found: {path}"], []

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return False, [f"Could not read file: {e}"], []

    headings = _h2_headings(content)
    task_name = path.stem

    if not _has_mission(headings):
        errors.append("Missing required section: ## Mission")

    if require_load_memory and not _has_load_memory(headings):
        errors.append("Missing required section: ## Load Session Memory or ## Load Memory")

    if require_execution and not _has_execution(headings):
        errors.append("Missing required section: ## Execution Rules or ## Execution Steps")

    for line_no, msg in _powershell_warnings(content):
        warnings.append(f"Line {line_no}: {msg}")

    valid = len(errors) == 0
    return valid, errors, warnings


def get_task_directory(workspace_root: Path) -> Path:
    """Return the task directory (skills/automation/tasks)."""
    return workspace_root / "skills" / "automation" / "tasks"


def validate_all_tasks(
    workspace_root: Path,
    *,
    allowed_exceptions: Tuple[str, ...] = (),
) -> Tuple[bool, List[Tuple[Path, List[str], List[str]]]]:
    """
    Validate all .md files in the task directory.

    allowed_exceptions: Task names (stem without .md) that may omit Load Memory.

    Returns:
        (all_valid, list of (path, errors, warnings) per file).
    """
    task_dir = get_task_directory(workspace_root)
    exceptions = set(LOAD_MEMORY_EXCEPTIONS) | set(allowed_exceptions)
    results: List[Tuple[Path, List[str], List[str]]] = []
    all_valid = True

    if not task_dir.exists():
        return False, [(task_dir, ["Task directory does not exist"], [])]

    for path in sorted(task_dir.glob("*.md")):
        minimal = path.stem in MINIMAL_TASKS
        exceptions_set = set(LOAD_MEMORY_EXCEPTIONS) | set(allowed_exceptions)
        require_load_memory = path.stem not in exceptions_set and not minimal
        require_execution = not minimal
        valid, errors, warnings = validate_task_file(
            path,
            require_load_memory=require_load_memory,
            require_execution=require_execution,
        )
        results.append((path, errors, warnings))
        if not valid:
            all_valid = False

    return all_valid, results
