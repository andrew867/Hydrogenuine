"""
Pack3 Phase 3: Tool abuse resistance — SSRF and allowlist policy tests.
"""

import pytest
from hg_core.policy.tool_policy import (
    BlockedAction,
    check_ssrf,
    check_request,
    extract_url_candidates,
)


def test_ssrf_blocks_localhost():
    assert check_ssrf("127.0.0.1") is not None
    assert check_ssrf("http://127.0.0.1/") is not None
    assert check_ssrf("localhost") is not None
    assert check_ssrf("http://localhost/") is not None
    assert check_ssrf("::1") is not None


def test_ssrf_blocks_metadata_ip():
    assert check_ssrf("169.254.169.254") is not None
    assert check_ssrf("http://169.254.169.254/") is not None


def test_ssrf_blocks_private_ranges():
    assert check_ssrf("10.0.0.1") is not None
    assert check_ssrf("172.16.0.1") is not None
    assert check_ssrf("192.168.1.1") is not None
    assert check_ssrf("http://10.0.0.5/api") is not None


def test_ssrf_blocks_file_and_gopher():
    assert check_ssrf("file:///etc/passwd") is not None
    assert check_ssrf("gopher://localhost/") is not None


def test_ssrf_allows_public_https():
    assert check_ssrf("https://example.com/path") is None
    assert check_ssrf("https://api.example.org") is None


def test_blocked_action_to_dict():
    b = BlockedAction(reason="test", code="ssrf_blocked", details={"x": 1})
    d = b.to_dict()
    assert d["reason"] == "test"
    assert d["code"] == "ssrf_blocked"
    assert d["details"] == {"x": 1}


def test_extract_url_candidates():
    assert extract_url_candidates({}) == []
    assert extract_url_candidates({"base_url": "https://api.example.com"}) == ["https://api.example.com"]
    assert extract_url_candidates({"url": "http://a.com", "other": 1}) == ["http://a.com"]
    assert extract_url_candidates({"endpoint": "https://x.y"}) == ["https://x.y"]


def test_check_request_ssrf_blocks():
    blocked = check_request("some.tool", {"base_url": "http://127.0.0.1/"}, {})
    assert blocked is not None
    assert blocked.code == "ssrf_blocked"


def test_check_request_allows_clean_inputs():
    assert check_request("some.tool", {"base_url": "https://example.com"}, {}) is None
    assert check_request("other.tool", {"message": "hi"}, {}) is None


def test_tool_allowlist_deterministic():
    # Allowlist: check_request returns None when tool is "allowed" (no SSRF); no role/tags in v1
    assert check_request("gateway.echo", {"message": "ok"}, {"name": "gateway.echo"}) is None
    blocked = check_request("gateway.echo", {"base_url": "http://192.168.1.1"}, {"name": "gateway.echo"})
    assert blocked is not None
