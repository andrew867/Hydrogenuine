"""Tests for hg_lib.config_loader (central config, env overrides, validation)."""

import os
from pathlib import Path

import pytest

from hg_lib.config_loader import load_config, get_config, CONFIG_FILENAMES, BOOL_KEYS
from hg_lib.errors import HydrogenuineError


def test_load_config_missing_file_returns_defaults(monkeypatch, tmp_path):
    """When no config file exists, returns default sections (empty dicts)."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    cfg = load_config(workspace_root=tmp_path)
    assert cfg.keys() == {"memory", "overseer", "platform"}
    assert cfg["memory"] == {}
    assert cfg["overseer"] == {}
    assert cfg["platform"] == {}


def test_load_config_from_fixture(monkeypatch, tmp_path):
    """Load config from memory/hg_config.yaml when present."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "hg_config.yaml"
    (tmp_path / "memory" / "hg_config.yaml").write_text(fixture.read_text())
    cfg = load_config(workspace_root=tmp_path)
    assert cfg["memory"]["base_path"] == "memory"
    assert cfg["memory"]["automation_path"] == "memory/automation"
    assert cfg["overseer"]["dry_run"] is False
    assert cfg["overseer"]["authority_config_path"] == "memory/overseer/authority-config.json"
    assert cfg["platform"]["default_timeout_sec"] == 30
    assert cfg["platform"]["retry_max"] == 3


def test_load_config_env_override(monkeypatch, tmp_path):
    """HG_OVERSER_DRY_RUN overrides file value."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "hg_config.yaml").write_text("overseer:\n  dry_run: false\n")
    monkeypatch.setenv("HG_OVERSER_DRY_RUN", "true")
    cfg = load_config(workspace_root=tmp_path)
    assert cfg["overseer"]["dry_run"] is True


def test_load_config_env_override_memory_section(monkeypatch, tmp_path):
    """HG_MEMORY_BASE_PATH sets memory.base_path."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_MEMORY_BASE_PATH", "custom/memory")
    cfg = load_config(workspace_root=tmp_path)
    assert cfg["memory"]["base_path"] == "custom/memory"


def test_load_config_invalid_section_raises(monkeypatch, tmp_path):
    """If a section is not a dict, validation raises."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "hg_config.yaml").write_text("overseer: not-a-dict\n")
    with pytest.raises(HydrogenuineError) as exc:
        load_config(workspace_root=tmp_path)
    assert "overseer" in str(exc.value) or "CONFIG_INVALID" in str(exc.value)


def test_load_config_strict_unknown_section_raises(monkeypatch, tmp_path):
    """With strict=True, unknown top-level key raises."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "hg_config.yaml").write_text("memory: {}\nextra_section: {}\n")
    with pytest.raises(HydrogenuineError) as exc:
        load_config(workspace_root=tmp_path, strict=True)
    assert "extra_section" in str(exc.value) or "Unknown" in str(exc.value)


def test_get_config_caches(monkeypatch, tmp_path):
    """get_config returns cached config after first load."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    c1 = get_config(workspace_root=tmp_path)
    c2 = get_config(workspace_root=tmp_path)
    assert c1 is c2


def test_get_config_reload(monkeypatch, tmp_path):
    """get_config(reload=True) forces fresh load."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    c1 = get_config(workspace_root=tmp_path, reload=True)
    c2 = get_config(workspace_root=tmp_path, reload=True)
    assert c1 is not c2
