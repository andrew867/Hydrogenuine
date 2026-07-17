"""Tests for hg_platforms.registry."""

import pytest

from hg_lib.errors import HydrogenuineError

from hg_platforms.registry import get_platform, get_task_for_platform_mode, list_platforms


def test_list_platforms_returns_builtins():
    platforms = list_platforms()
    assert "moltbook" in platforms
    assert "fourclaw" in platforms
    assert "agentchan" in platforms
    assert "moltx" in platforms
    assert "moltstack" in platforms
    assert "aichan" in platforms


def test_get_platform_for_builtins():
    for pid in ["moltbook", "fourclaw", "agentchan", "moltx", "moltstack", "aichan"]:
        p = get_platform(pid)
        assert p.platform_id == pid
        assert p.get_status()["platform"] == pid


def test_get_platform_unknown_raises():
    with pytest.raises(HydrogenuineError) as exc_info:
        get_platform("nonexistent-platform-xyz")
    assert exc_info.value.code == "UNKNOWN_PLATFORM"


def test_get_task_for_platform_mode():
    assert get_task_for_platform_mode("moltbook", "auto-post") == "moltbook-auto-post"
    assert get_task_for_platform_mode("moltbook", "engage") == "moltbook-engage"
    assert get_task_for_platform_mode("fourclaw", "engage") == "fourclaw-engage"
    assert get_task_for_platform_mode("moltstack", "draft") == "moltstack-draft"
    assert get_task_for_platform_mode("moltstack", "publish") == "moltstack-publish"


def test_get_task_for_platform_mode_unknown():
    assert get_task_for_platform_mode("moltbook", "publish") is None
    assert get_task_for_platform_mode("unknown", "auto-post") is None
