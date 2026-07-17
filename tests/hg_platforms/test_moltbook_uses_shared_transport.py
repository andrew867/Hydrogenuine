"""Smoke test: moltbook uses shared transport; get path runs with mocked transport."""

from unittest.mock import patch

from hg_platforms.moltbook import moltbook_api_client


def test_moltbook_get_agent_status_uses_shared_transport():
    """get_agent_status() runs and returns data when shared transport returns success (mocked)."""
    with patch.object(moltbook_api_client, "load_api_key", return_value="test_key"):
        with patch.object(moltbook_api_client, "request_with_retry") as mock_request:
            mock_request.return_value = {"status": "claimed"}
            result = moltbook_api_client.get_agent_status()
    assert result.get("status") == "claimed"
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert "agents/status" in (args[1] or "")
    assert kwargs.get("headers", {}).get("Authorization") == "Bearer test_key"


def test_moltbook_get_feed_uses_shared_transport():
    """get_feed() runs and returns posts when shared transport returns success (mocked)."""
    with patch.object(moltbook_api_client, "load_api_key", return_value="test_key"):
        with patch.object(moltbook_api_client, "request_with_retry") as mock_request:
            mock_request.return_value = {"posts": [{"id": "p1", "title": "Hello"}]}
            result = moltbook_api_client.get_feed(sort="hot", limit=10)
    assert "posts" in result
    assert len(result["posts"]) == 1
    assert result["posts"][0]["id"] == "p1"
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert "feed" in (args[1] or "")
