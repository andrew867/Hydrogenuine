"""Tests for platform interface (SocialPlatform mock) and shared transport (retry/backoff)."""

from unittest.mock import MagicMock

import pytest

from hg_platforms.base import SocialPlatform
from hg_platforms.registry import get_platform, list_platforms


def test_list_platforms_includes_builtins():
    """list_platforms returns built-in platform IDs including fourclaw and moltbook."""
    platforms = list_platforms()
    assert "fourclaw" in platforms
    assert "moltbook" in platforms
    assert "agentchan" in platforms


def test_get_platform_returns_social_platform():
    """get_platform(fourclaw) returns an object implementing SocialPlatform."""
    client = get_platform("fourclaw")
    assert hasattr(client, "platform_id")
    assert client.platform_id == "fourclaw"
    assert hasattr(client, "post")
    assert hasattr(client, "get_feed")
    assert hasattr(client, "engage")
    assert hasattr(client, "get_profile")
    assert hasattr(client, "get_status")


def test_mock_client_implements_interface():
    """A mock implementing SocialPlatform can be called (post, get_feed)."""
    mock: SocialPlatform = MagicMock(spec=SocialPlatform)
    mock.platform_id = "test_platform"
    mock.post.return_value = {"ok": True, "post_id": "123"}
    mock.get_feed.return_value = {"ok": True, "posts": []}
    assert mock.post("Title", "Content") == {"ok": True, "post_id": "123"}
    assert mock.get_feed(limit=10) == {"ok": True, "posts": []}
    mock.post.assert_called_once_with("Title", "Content")
    mock.get_feed.assert_called_once_with(limit=10)
