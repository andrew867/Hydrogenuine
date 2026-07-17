"""Playwright UX proofs for EXCITON — real browser clicks and live API data."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
SERVER_SCRIPT = WORKSPACE / "scripts" / "dev" / "exciton_api_server.py"

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Page, sync_playwright  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def exciton_server():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT), "--port", str(port)],
        cwd=str(WORKSPACE),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 90
    last_err = ""
    while time.time() < deadline:
        try:
            import urllib.request

            with urllib.request.urlopen(f"{base}/api/exciton/status", timeout=30) as resp:
                if resp.status == 200:
                    break
        except Exception as exc:
            last_err = str(exc)
            time.sleep(1)
    else:
        proc.kill()
        raise RuntimeError(f"EXCITON server failed to start: {last_err}")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _api_json(page: Page, url: str) -> dict:
    return page.evaluate(
        """async (u) => {
            const r = await fetch(u);
            return await r.json();
        }""",
        url,
    )


def test_exciton_home_loads_live_snapshot(exciton_server: str, page: Page) -> None:
    page.goto(exciton_server + "/")
    page.wait_for_selector("#snapshot-meta", timeout=10000)
    meta = page.locator("#snapshot-meta").inner_text()
    assert meta.strip()

    status = _api_json(page, exciton_server + "/api/exciton/status")
    assert status.get("ok") is True
    snap = status.get("snapshot") or {}
    assert snap.get("advisory_only") is True
    assert snap.get("dangerous_actions_disabled") is True
    verdict = snap.get("overall_verdict", "")
    assert verdict.startswith(("GREEN", "YELLOW", "RED"))
    assert len(snap.get("panels") or []) > 0


def test_exciton_refresh_button_updates_ui(exciton_server: str, page: Page) -> None:
    page.goto(exciton_server + "/")
    page.wait_for_selector('[data-control-id="REFRESH_STATUS"]')
    before = _api_json(page, exciton_server + "/api/exciton/status")
    page.click('[data-control-id="REFRESH_STATUS"]')
    page.wait_for_timeout(500)
    after = _api_json(page, exciton_server + "/api/exciton/status")
    assert after.get("ok") is True
    assert before.get("snapshot") is not None
    assert after.get("snapshot") is not None


def test_exciton_nav_sections_and_stop_panic(exciton_server: str, page: Page) -> None:
    page.goto(exciton_server + "/")
    page.wait_for_selector(".nav-item")

    page.click('button.nav-item[data-section="soak"]')
    page.wait_for_selector("#stop-panic-copy")
    copy = page.locator("#stop-panic-copy").inner_text()
    assert "STOP:" in copy
    assert "PANIC:" in copy

    stop_buttons = page.locator('[data-control-id="STOP_SOAK"], [data-control-id="STOP_AGENT"]')
    assert stop_buttons.count() >= 1
    panic_buttons = page.locator('[data-control-id="PANIC_STOP"]')
    assert panic_buttons.count() >= 1

    matrix = _api_json(page, exciton_server + "/api/exciton/control-matrix")
    assert matrix.get("ok") is True
    controls_list = matrix.get("matrix") or []
    by_id = {c.get("control_id"): c for c in controls_list if isinstance(c, dict)}
    publish = by_id.get("APPROVE_SOCIAL_PUBLISH") or {}
    assert publish.get("decision") == "QUEUE_FOR_OPERATOR" or publish.get("forbidden") is True


def test_exciton_send_disabled_and_operator_queue(exciton_server: str, page: Page) -> None:
    page.goto(exciton_server + "/")
    page.click('button.nav-item[data-section="message-center"]')
    send_btn = page.locator("#send-message-btn")
    page.wait_for_selector("#send-message-btn")
    assert send_btn.is_disabled()

    page.click('button.nav-item[data-section="operator-queue"]')
    page.wait_for_timeout(300)
    queue = _api_json(page, exciton_server + "/api/exciton/operator-queue")
    assert queue.get("ok") is True


def test_exciton_dev_json_matches_api(exciton_server: str, page: Page) -> None:
    page.goto(exciton_server + "/")
    page.wait_for_selector("#snapshot-meta", timeout=30000)
    page.click('[data-control-id="REFRESH_STATUS"]')
    page.wait_for_function("document.getElementById('dev-raw-json').textContent.length > 20")
    page.click('button.nav-item[data-section="dev"]')
    page.wait_for_function("document.body.getAttribute('data-active-section') === 'dev'")
    raw = page.locator("#dev-raw-json").text_content() or ""
    assert raw.strip()
    ui_payload = json.loads(raw)
    api_payload = _api_json(page, exciton_server + "/api/exciton/status")
    api_verdict = (api_payload.get("snapshot") or {}).get("overall_verdict")
    ui_verdict = ((ui_payload.get("status") or {}).get("snapshot") or {}).get("overall_verdict")
    assert ui_verdict == api_verdict


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        yield context
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context):
    pg = browser_context.new_page()
    yield pg
    pg.close()
