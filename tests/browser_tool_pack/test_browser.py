"""Browser tool pack tests — fixture defaults plus optional live HTTP."""

from __future__ import annotations

import pytest

from hg_runtime.cloud_browser_governance.browser import (
    LIVE_TEST_URL,
    browser_extract_text,
    browser_fetch_page,
    browser_form_detect,
    browser_form_submit,
    browser_open_url_request,
    browser_read_fixture,
    browser_read_page,
    browser_screenshot,
    browser_search_public_web_request,
    execute_browser_tool,
    live_browser_allowed,
)


def test_fixture_not_proof():
    r = browser_read_fixture()
    assert r["is_proof"] is False
    assert r["live_fetch"] is False


def test_form_submit_full_stop():
    r = browser_form_submit(url="https://x.com/login")
    assert r["decision"] == "FULL_STOP"


def test_form_detect_login_risk():
    r = browser_form_detect(html="<form>login password</form>")
    assert r["decision"] == "FULL_STOP"
    assert r["risks"]["login_detected"] is True


def test_open_fixture_when_live_disabled():
    r = browser_open_url_request(url="fixture://local")
    assert r["schema"] in {"browser-read-result", "browser-open-denied"}


def test_execute_browser_tools_fixture_path():
    read = execute_browser_tool("browser_read_page", {"url": "fixture://local"})
    assert read["schema"] in {"browser-read-result", "browser-read-denied"}
    extract = execute_browser_tool("browser_extract_text", {"url": "fixture://local"})
    assert extract["schema"] == "browser-extract-text"
    shot = execute_browser_tool("browser_screenshot", {"url": "fixture://local"})
    assert shot["schema"] == "browser-screenshot"


@pytest.mark.browser_live
def test_live_open_example_com():
    r = browser_open_url_request(url=LIVE_TEST_URL)
    assert r["schema"] in {"browser-read-result", "browser-open-warning"}
    assert r.get("live_fetch") is True
    assert r.get("status") == 200
    preview = (r.get("text_preview") or "").lower()
    assert "example" in preview or "domain" in preview


@pytest.mark.browser_live
def test_live_read_page_content_hash():
    r = browser_read_page(url=LIVE_TEST_URL)
    assert r["schema"] in {"browser-read-result", "browser-open-warning"}
    assert r.get("live_fetch") is True
    assert r.get("content_hash")
    assert len(r.get("plain_text") or r.get("text_preview") or "") > 20


@pytest.mark.browser_live
def test_live_extract_text():
    r = browser_extract_text(url=LIVE_TEST_URL)
    assert r["schema"] == "browser-extract-text"
    assert r.get("live_fetch") is True
    assert len(r.get("text") or "") > 10


@pytest.mark.browser_live
def test_live_screenshot_artifact():
    r = browser_screenshot(url=LIVE_TEST_URL)
    assert r["schema"] == "browser-screenshot"
    assert r.get("captured") is True
    assert r.get("artifact_ref")
    assert r.get("live_fetch") is True


@pytest.mark.browser_live
def test_live_fetch_page_direct():
    r = browser_fetch_page(url=LIVE_TEST_URL)
    assert r.get("live_fetch") is True
    assert "sk-" not in str(r)
    assert "api_key" not in str(r).lower()


@pytest.mark.browser_live
def test_live_search_public_web():
    r = browser_search_public_web_request(query="example domain")
    assert r["schema"] in {"browser-read-result", "browser-open-warning", "browser-read-error"}
    if r["schema"] == "browser-read-result":
        assert r.get("live_fetch") is True


@pytest.mark.browser_live
def test_live_execute_browser_tool_read():
    r = execute_browser_tool("browser_read_page", {"url": LIVE_TEST_URL})
    assert r.get("live_fetch") is True
    assert live_browser_allowed() is True
