"""Smoke test: fourclaw uses shared transport; list_boards (get path) runs with mocked transport."""

from unittest.mock import patch

from hg_platforms.fourclaw import fourclaw_api_client


def test_fourclaw_list_boards_uses_shared_transport():
    """list_boards() runs and returns data when shared transport returns success (mocked)."""
    with patch.object(fourclaw_api_client, "load_api_key", return_value="test_key"):
        with patch.object(fourclaw_api_client, "request_with_retry") as mock_request:
            mock_request.return_value = {"boards": [{"slug": "general"}, {"slug": "singularity"}]}
            result = fourclaw_api_client.list_boards()
    assert "boards" in result
    assert len(result["boards"]) == 2
    assert result["boards"][0]["slug"] == "general"
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert "boards" in (args[1] or "")
    assert kwargs.get("headers", {}).get("Authorization") == "Bearer test_key"
