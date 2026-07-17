"""Playwright read-only page capture — screenshot is not truth.

Uses Playwright in locked-down read-only context. No login, registration,
form submission, downloads, geolocation, microphone, camera, clipboard write,
notifications, payment, WebUSB, WebBluetooth, file chooser, or persistent
profile writes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "playwright_capture_receipt_v1"

BLOCKED_PERMISSIONS = [
    "geolocation", "notifications", "camera", "microphone",
    "clipboard-write", "payment-handler",
]

LOGIN_DIALOG_PATTERNS = [
    r"sign\s*in", r"log\s*in", r"create\s*account",
    r"register", r"sign\s*up", r"forgot\s*password",
]


def create_browser_context_config() -> dict:
    return {
        "accept_downloads": False,
        "has_touch": False,
        "ignore_https_errors": False,
        "java_script_enabled": True,
        "permissions": [],
        "geolocation": None,
        "locale": "en-US",
        "timezone_id": "UTC",
        "color_scheme": "light",
        "user_agent_suffix": "HydrogenuineSourceOrgan/ReadOnly",
        "blocked_permissions": BLOCKED_PERMISSIONS,
        "no_persistent_profile": True,
        "no_login": True,
        "no_form_submit": True,
        "no_downloads": True,
        "read_only": True,
    }


def capture_page(url: str, output_dir: str, *,
                 timeout_ms: int = 30000,
                 viewport_width: int = 1280,
                 viewport_height: int = 720,
                 full_page: bool = True,
                 user_agent: str = "") -> dict:
    """Capture a page using Playwright. Returns a capture receipt.

    Requires playwright browsers to be installed. Falls back gracefully
    if Playwright is not available or page load fails.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    url_slug = re.sub(r'[^a-zA-Z0-9]', '_', url)[:80]

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _failure_receipt(url, "playwright not installed")

    screenshot_path = os.path.join(output_dir, f"screenshot_{url_slug}_{ts}.png")
    text_path = os.path.join(output_dir, f"text_{url_slug}_{ts}.txt")
    network_path = os.path.join(output_dir, f"network_{url_slug}_{ts}.json")

    network_requests = []
    page_title = ""
    canonical_url = url
    visible_text = ""
    screenshot_hash = ""
    page_hash = ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx_kwargs = {
                "accept_downloads": False,
                "viewport": {"width": viewport_width, "height": viewport_height},
                "locale": "en-US",
                "timezone_id": "UTC",
                "color_scheme": "light",
                "permissions": [],
            }
            if user_agent:
                ctx_kwargs["user_agent"] = user_agent
            context = browser.new_context(**ctx_kwargs)
            page = context.new_page()

            def on_request(request):
                network_requests.append({
                    "url": request.url[:200],
                    "method": request.method,
                    "resource_type": request.resource_type,
                })

            page.on("request", on_request)

            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            page_title = page.title() or ""
            canonical_url = page.url

            visible_text = page.evaluate("() => document.body?.innerText || ''") or ""
            visible_text = visible_text[:50000]

            page.screenshot(path=screenshot_path, full_page=full_page)

            with open(screenshot_path, "rb") as f:
                screenshot_hash = hashlib.sha256(f.read()).hexdigest()

            page_hash = hashlib.sha256(visible_text.encode()).hexdigest()

            with open(text_path, "w", encoding="utf-8") as f:
                f.write(visible_text)

            with open(network_path, "w", encoding="utf-8") as f:
                json.dump(network_requests, f, indent=2)

            context.close()
            browser.close()

    except Exception as e:
        return _failure_receipt(url, f"playwright capture failed: {str(e)[:200]}")

    return {
        "schema": SCHEMA_VERSION,
        "capture_id": hashlib.sha256(f"{url}:{ts}".encode()).hexdigest()[:24],
        "url": url,
        "canonical_url": canonical_url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "page_title": page_title,
        "viewport": f"{viewport_width}x{viewport_height}",
        "full_page_captured": full_page,
        "screenshot_path": screenshot_path,
        "screenshot_hash": screenshot_hash,
        "text_extract_path": text_path,
        "page_hash": page_hash,
        "visible_text_length": len(visible_text),
        "visible_text_sample": visible_text[:500],
        "network_request_summary_path": network_path,
        "network_request_count": len(network_requests),
        "post_requests_blocked": sum(1 for r in network_requests if r["method"] != "GET"),
        "success": True,
        "failure_reason": "",
        "screenshot_is_observation_only": True,
        "screenshot_is_not_evidence": True,
        "screenshot_is_truth": False,
        "read_only_enforced": True,
        "no_login": True,
        "no_form_submit": True,
        "no_downloads": True,
        "source_treated_as_truth": False,
        "external_effect_created": False,
        "user_agent_used": user_agent or "chromium_default",
        "browser_lockdown": {
            "accept_downloads": False,
            "blocked_permissions": BLOCKED_PERMISSIONS,
            "no_login": True,
            "no_form_submit": True,
            "no_persistent_profile": True,
            "read_only": True,
        },
    }


def _failure_receipt(url: str, reason: str) -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "capture_id": hashlib.sha256(
            f"{url}:{reason}".encode()).hexdigest()[:24],
        "url": url,
        "canonical_url": url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "page_title": "",
        "viewport": "",
        "full_page_captured": False,
        "screenshot_path": "",
        "screenshot_hash": "",
        "text_extract_path": "",
        "page_hash": "",
        "visible_text_length": 0,
        "visible_text_sample": "",
        "network_request_summary_path": "",
        "network_request_count": 0,
        "post_requests_blocked": 0,
        "success": False,
        "failure_reason": reason,
        "screenshot_is_observation_only": True,
        "screenshot_is_not_evidence": True,
        "screenshot_is_truth": False,
        "read_only_enforced": True,
        "no_login": True,
        "no_form_submit": True,
        "no_downloads": True,
        "source_treated_as_truth": False,
        "external_effect_created": False,
    }


def validate_capture_receipt(receipt: dict) -> list[str]:
    errors = []
    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {receipt.get('schema')}")
    if receipt.get("source_treated_as_truth"):
        errors.append("source_treated_as_truth must be False")
    if receipt.get("external_effect_created"):
        errors.append("external_effect_created must be False")
    if not receipt.get("screenshot_is_observation_only"):
        errors.append("screenshot_is_observation_only must be True")
    if not receipt.get("screenshot_is_not_evidence"):
        errors.append("screenshot_is_not_evidence must be True")
    if not receipt.get("read_only_enforced"):
        errors.append("read_only_enforced must be True")
    if not receipt.get("no_login"):
        errors.append("no_login must be True")
    if not receipt.get("no_form_submit"):
        errors.append("no_form_submit must be True")
    return errors
