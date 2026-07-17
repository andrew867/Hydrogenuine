"""Tests for hg_persona.loader."""

import pytest

from hg_persona.loader import load_platform_persona, update_platform_persona


def test_load_platform_persona_returns_dict(tmp_path, monkeypatch):
    """load_platform_persona returns dict with soul, heart, identity keys."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "skills" / "automation" / "personas" / "test" / "default").mkdir(parents=True)
    (tmp_path / "skills" / "automation" / "personas" / "test" / "default" / "SOUL.md").write_text(
        "# Soul", encoding="utf-8"
    )
    persona = load_platform_persona("test")
    assert "soul" in persona
    assert "heart" in persona
    assert "identity" in persona
    assert persona["soul"] == "# Soul"


def test_load_platform_persona_missing_files_returns_empty_strings(tmp_path, monkeypatch):
    """Missing files yield empty strings."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "skills" / "automation" / "personas" / "empty" / "default").mkdir(parents=True)
    persona = load_platform_persona("empty")
    assert persona["soul"] == ""
    assert persona["heart"] == ""
    assert persona["identity"] == ""


def test_update_platform_persona_allowed_file(tmp_path, monkeypatch):
    """update_platform_persona writes allowed files."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    (tmp_path / "skills" / "automation" / "personas" / "test" / "default").mkdir(parents=True)
    result = update_platform_persona("test", "default", "SOUL.md", "# New Soul Content")
    assert result is True
    content = (tmp_path / "skills" / "automation" / "personas" / "test" / "default" / "SOUL.md").read_text()
    assert content == "# New Soul Content"


def test_update_platform_persona_disallowed_file():
    """update_platform_persona rejects non-persona files."""
    result = update_platform_persona("test", "default", "evil.py", "malicious")
    assert result is False
