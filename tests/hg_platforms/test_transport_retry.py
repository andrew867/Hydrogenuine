"""Tests for shared transport retry/backoff (429, 5xx, connection)."""

from unittest.mock import patch, MagicMock

import pytest

from hg_platforms.transport import request_with_retry


def test_request_with_retry_429_then_success():
    """On 429 with Retry-After, transport retries and returns success on second attempt."""
    responses = [
        MagicMock(status_code=429, headers={"Retry-After": "1"}, json=lambda: {"retry_after": 1}),
        MagicMock(status_code=200, json=lambda: {"thread": {"id": "123"}}, raise_for_status=MagicMock()),
    ]
    call_count = [0]

    def fake_request(*args, **kwargs):
        resp = responses[min(call_count[0], len(responses) - 1)]
        call_count[0] += 1
        if resp.status_code != 200:
            return resp
        resp.raise_for_status = MagicMock()
        return resp

    with patch("hg_platforms.transport.requests") as m_requests:
        m_requests.get = fake_request
        m_requests.post = fake_request
        m_requests.patch = fake_request
        m_requests.delete = fake_request
        with patch("hg_platforms.transport.time.sleep"):
            result = request_with_retry("GET", "https://api.example/boards", retry_max=3)
    assert result.get("thread", {}).get("id") == "123"
    assert call_count[0] >= 2


def test_request_with_retry_429_exhausted_returns_error():
    """When 429 with no Retry-After persists, return error dict without retrying."""
    resp_429 = MagicMock(status_code=429, headers={}, json=lambda: {})
    with patch("hg_platforms.transport.requests") as m_requests:
        m_requests.get.return_value = resp_429
        with patch("hg_platforms.transport.time.sleep"):
            result = request_with_retry("GET", "https://api.example/boards", retry_max=2)
    assert result.get("ok") is False
    assert result.get("status_code") == 429
    assert "Rate limit" in str(result.get("error", ""))


def test_request_with_retry_success_returns_json():
    """On 200, transport returns parsed JSON."""
    resp = MagicMock(status_code=200, json=lambda: {"boards": [{"slug": "general"}]})
    resp.raise_for_status = MagicMock()
    with patch("hg_platforms.transport.requests") as m_requests:
        m_requests.get.return_value = resp
        result = request_with_retry("GET", "https://api.example/boards")
    assert result.get("boards") == [{"slug": "general"}]
