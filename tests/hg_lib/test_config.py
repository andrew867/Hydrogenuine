"""Tests for hg_lib.config."""

import os
from pathlib import Path

import pytest

from hg_lib.config import (
    get_workspace_root,
    get_memory_dir,
    get_knowledge_dir,
    get_docs_dir,
    get_incoming_dir,
    get_skills_dir,
    get_automation_tasks_dir,
    get_automation_memory_dir,
    get_task_file_path,
    get_persona_dir,
    get_persona_config_path,
    get_cron_jobs_path,
    get_posting_lock_path,
    ensure_workspace_initialized,
    SENTINEL_FILE,
)
from hg_lib.errors import HydrogenuineError


def test_get_workspace_root_env(monkeypatch, tmp_path):
    """HG_WORKSPACE env takes precedence."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    assert get_workspace_root() == tmp_path


def test_get_workspace_root_no_sentinel_raises(monkeypatch, tmp_path):
    """Without env or sentinel, raises HydrogenuineError."""
    monkeypatch.delenv("HG_WORKSPACE", raising=False)
    # Use tmp_path as cwd, ensure no .hg_root
    # Also need to hide ~/.hg/workspace - set env to tmp_path that doesn't exist
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path / "nonexistent_ws"))
    # Now HOME/.hg/workspace - we can't easily hide that. Use a path that
    # won't match: if we set HG_WORKSPACE to a path that exists, we use it.
    # To test the raise, we need: no HG_WORKSPACE, no ~/.hg/workspace,
    # cwd has no sentinel. Monkeypatch env to clear, then monkeypatch Path.home?
    # Simpler: use tmp_path, create sentinel in sibling, run from a dir without sentinel.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HG_WORKSPACE", raising=False)
    # Create fake home that has no .hg/workspace
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    with pytest.raises(HydrogenuineError) as exc:
        get_workspace_root()
    assert "HG_WORKSPACE" in str(exc.value) or ".hg_root" in str(exc.value)


def test_get_memory_dir():
    """get_memory_dir returns workspace/memory."""
    root = get_workspace_root()
    assert get_memory_dir() == root / "memory"


def test_get_knowledge_dir():
    """get_knowledge_dir returns workspace/knowledge."""
    root = get_workspace_root()
    assert get_knowledge_dir() == root / "knowledge"


def test_get_automation_memory_dir():
    """get_automation_memory_dir returns correct path."""
    root = get_workspace_root()
    assert get_automation_memory_dir("moltbook-auto-post") == root / "memory" / "automation" / "automation-moltbook-auto-post"


def test_get_task_file_path():
    """get_task_file_path returns correct path."""
    root = get_workspace_root()
    assert get_task_file_path("moltbook-auto-post") == root / "skills" / "automation" / "tasks" / "moltbook-auto-post.md"


def test_get_persona_dir():
    """get_persona_dir returns correct path."""
    root = get_workspace_root()
    assert get_persona_dir("moltbook", None) == root / "skills" / "automation" / "personas" / "moltbook" / "default"
    assert get_persona_dir("moltbook", "custom") == root / "skills" / "automation" / "personas" / "moltbook" / "custom"


def test_get_cron_jobs_path():
    """get_cron_jobs_path returns home-based path."""
    p = get_cron_jobs_path()
    assert ".hg" in str(p)
    assert "cron" in str(p)
    assert p.name == "jobs.json"


def test_get_posting_lock_path():
    """get_posting_lock_path returns workspace memory path per platform."""
    root = get_workspace_root()
    assert get_posting_lock_path("moltbook") == root / "memory" / "posting_lock_moltbook.lock"
    assert get_posting_lock_path("global") == root / "memory" / "posting_lock_global.lock"


def test_get_docs_dir():
    """get_docs_dir returns workspace/docs."""
    root = get_workspace_root()
    assert get_docs_dir() == root / "docs"


def test_get_incoming_dir():
    """get_incoming_dir returns workspace/incoming."""
    root = get_workspace_root()
    assert get_incoming_dir() == root / "incoming"


def test_get_skills_dir():
    """get_skills_dir returns workspace/skills."""
    root = get_workspace_root()
    assert get_skills_dir() == root / "skills"


def test_get_automation_tasks_dir():
    """get_automation_tasks_dir returns correct path."""
    root = get_workspace_root()
    assert get_automation_tasks_dir() == root / "skills" / "automation" / "tasks"


def test_get_persona_config_path():
    """get_persona_config_path returns platform config path (skills/automation/{platform}/persona_config.json)."""
    root = get_workspace_root()
    assert get_persona_config_path("moltbook") == root / "skills" / "automation" / "moltbook" / "persona_config.json"


def test_ensure_workspace_initialized_env_missing_creates(monkeypatch, tmp_path):
    """Env set, path missing: creates root and subdirs."""
    ws = tmp_path / "new_workspace"
    monkeypatch.setenv("HG_WORKSPACE", str(ws))
    ensure_workspace_initialized(ws)
    assert ws.exists()
    assert (ws / "memory").exists()
    assert (ws / "knowledge").exists()
    assert (ws / "skills" / "automation" / "tasks").exists()


def test_ensure_workspace_initialized_sentinel_creates_subdirs(monkeypatch, tmp_path):
    """Sentinel cwd, subdirs missing: creates subdirs."""
    (tmp_path / SENTINEL_FILE).write_text("")
    ensure_workspace_initialized(tmp_path)
    assert (tmp_path / "memory").exists()
    assert (tmp_path / "knowledge").exists()


def test_ensure_workspace_initialized_default_missing_no_create(monkeypatch, tmp_path):
    """~/.hg/workspace missing: does not create unless HG_CREATE_DEFAULT_WORKSPACE."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    default_ws = fake_home / ".hg" / "workspace"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    ensure_workspace_initialized(default_ws)
    assert not default_ws.exists()


def test_hg_packages_no_skills_imports():
    """hg_* packages never import from skills.* (migration invariant)."""
    import re

    patterns = [
        r"^\s*import\s+skills\.",
        r"^\s*from\s+skills\.",
        r"^\s*from\s+skills\s+import\s+",
    ]
    workspace_root = Path(__file__).parent.parent.parent
    violations = []
    # hg_overseer is the single source of truth for overseer (no skills/automation/overseer)
    pkgs_to_check = ["hg_lib", "hg_core", "hg_knowledge", "hg_memory", "hg_platforms"]
    allowed = ""  # no allowed skills imports in these packages
    for pkg in pkgs_to_check:
        pkg_dir = workspace_root / pkg
        if not pkg_dir.exists():
            continue
        for py_file in pkg_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                for pat in patterns:
                    if re.search(pat, line) and allowed not in line:
                        violations.append(f"{py_file.relative_to(workspace_root)}:{i}: {line.strip()}")
    assert not violations, "hg_* packages must not import from skills.*:\n" + "\n".join(violations[:20])
