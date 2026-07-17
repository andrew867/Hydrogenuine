"""
Phase 0: Overseer single source of truth.

Tests that overseer entry point works and no code imports from skills.automation.overseer.
"""

import subprocess
import sys
from pathlib import Path


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_overseer_entry_help():
    """hg-overseer --help exits 0 and prints usage."""
    result = subprocess.run(
        [sys.executable, "-m", "hg_overseer.main", "--help"],
        capture_output=True,
        text=True,
        cwd=str(_workspace_root()),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "Hydrogenuine" in result.stdout or "overseer" in result.stdout.lower()


def test_no_skills_automation_overseer_imports():
    """No Python file (except under temp/.cursor/skills/automation/overseer) imports from skills.automation.overseer."""
    root = _workspace_root()
    skip_dirs = {"temp", ".cursor", "venv", ".git", "__pycache__", "node_modules", ".pytest_cache"}
    skip_under = (root / "skills" / "automation" / "overseer").resolve() if (root / "skills" / "automation" / "overseer").exists() else None
    bad = []
    for path in root.rglob("*.py"):
        try:
            rel = path.resolve().relative_to(root)
        except ValueError:
            continue
        if any(part in skip_dirs for part in rel.parts):
            continue
        if skip_under and path.resolve().is_relative_to(skip_under):
            continue
        if path.name == "test_overseer_single_source.py":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line in lines:
            s = line.strip()
            if s.startswith("#"):
                continue
            if "skills.automation.overseer" in s and (
                s.startswith("from skills.automation.overseer")
                or "import skills.automation.overseer" in s
                or "@patch(" in s and "skills.automation.overseer" in s
                or "skills.automation.overseer." in s
            ):
                bad.append(f"{rel}:{s[:80]}")
                break
    assert not bad, "Overseer imports must use hg_overseer only. Found: " + "; ".join(bad)


def test_run_overseer_task_import_from_hg_overseer():
    """run_overseer_task is importable from hg_overseer (single source of truth)."""
    from hg_overseer.overseer_core.overseer_main import run_overseer_task

    assert callable(run_overseer_task)
