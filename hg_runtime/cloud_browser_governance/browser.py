"""Governed browser tool pack — read-only by default, live HTTP when enabled."""

from __future__ import annotations

import html as html_lib
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.cloud_browser_governance.lattice import ApprovalDecisionEngine
from hg_runtime.cloud_browser_governance.types import advisory_envelope, redact_secrets, stable_hash

WORKSPACE = Path(__file__).resolve().parents[2]
FIXTURE_PAGE = WORKSPACE / "docs" / "planning" / "tool_capability_fabric" / "TOOL_CAPABILITY_FABRIC_SPEC.md"
BROWSER_ARTIFACT_DIR = WORKSPACE / ".hg-local" / "browser" / "artifacts"
LIVE_TEST_URL = os.environ.get("HG_BROWSER_LIVE_TEST_URL", "https://example.com")

LOGIN_PATTERNS = re.compile(r"(?i)(login|sign\s*in|password|credential)")
ACCOUNT_PATTERNS = re.compile(r"(?i)(create\s+account|sign\s*up|register)")
PAYMENT_PATTERNS = re.compile(r"(?i)(checkout|payment|credit\s*card)")
TAG_RE = re.compile(r"<[^>]+>")


def external_network_enabled() -> bool:
    return os.environ.get("HG_EXTERNAL_NETWORK_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def live_browser_allowed() -> bool:
    return external_network_enabled() and os.environ.get("HG_ALLOW_LIVE_BROWSER_TEST", "false").strip().lower() in {"1", "true", "yes"}


def _detect_risks(text: str) -> dict[str, bool]:
    return {
        "login_detected": bool(LOGIN_PATTERNS.search(text)),
        "account_creation_detected": bool(ACCOUNT_PATTERNS.search(text)),
        "payment_detected": bool(PAYMENT_PATTERNS.search(text)),
    }


def _strip_html(html: str) -> str:
    text = TAG_RE.sub(" ", html)
    return html_lib.unescape(re.sub(r"\s+", " ", text)).strip()


def _http_get(url: str, *, timeout: float = 20.0) -> tuple[int, str, str]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Hydrogenuine-Browser-Pack/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(500_000)
        ctype = resp.headers.get("Content-Type", "")
        body = raw.decode("utf-8", errors="ignore")
        return int(getattr(resp, "status", 200) or 200), body, ctype


def browser_read_fixture(*, url: str = "fixture://local") -> dict[str, Any]:
    text = FIXTURE_PAGE.read_text(encoding="utf-8", errors="ignore")[:4000] if FIXTURE_PAGE.is_file() else "fixture page"
    risks = _detect_risks(text)
    content_hash = stable_hash({"url": url, "text": text[:500]})
    return advisory_envelope(
        schema="browser-read-result",
        url=url,
        method="GET",
        status=200,
        content_hash=content_hash,
        text_preview=text[:500],
        plain_text=text[:2000],
        risks=risks,
        live_fetch=False,
        is_proof=False,
        live_side_effect=False,
    )


def browser_fetch_page(*, url: str, method: str = "GET") -> dict[str, Any]:
    """Fetch page via fixture or live HTTP GET depending on policy."""
    if url.startswith("fixture://") or not live_browser_allowed():
        return browser_read_fixture(url=url)
    if method.upper() != "GET":
        return advisory_envelope(schema="browser-open-denied", reason="non_get_forbidden", method=method, url=redact_secrets(url))
    try:
        status, body, ctype = _http_get(url)
        plain = _strip_html(body) if "<html" in body.lower() or "<body" in body.lower() else body
        risks = _detect_risks(body)
        schema = "browser-read-result"
        decision = None
        if any(risks.values()):
            schema = "browser-open-warning"
            decision = "AUTO_WARN"
        payload = advisory_envelope(
            schema=schema,
            url=url,
            method="GET",
            status=status,
            content_type=ctype,
            content_hash=stable_hash({"url": url, "body": body[:500]}),
            text_preview=plain[:500],
            plain_text=plain[:4000],
            risks=risks,
            decision=decision,
            live_fetch=True,
            is_proof=False,
            live_side_effect=False,
        )
        return payload
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return advisory_envelope(schema="browser-read-error", url=url, error=str(exc), live_fetch=True, live_side_effect=False)


def browser_open_url_request(*, url: str, method: str = "GET") -> dict[str, Any]:
    lattice = ApprovalDecisionEngine()
    decision = lattice.evaluate(action_id="browser_open_url_request", parameters={"url": url, "method": method}, external_network=external_network_enabled())
    if decision["decision"] not in {"AUTO_APPROVE", "AUTO_WARN"}:
        return advisory_envelope(schema="browser-open-denied", decision=decision, url=redact_secrets(url))
    return browser_fetch_page(url=url, method=method)


def browser_read_page(*, url: str) -> dict[str, Any]:
    lattice = ApprovalDecisionEngine()
    decision = lattice.evaluate(action_id="browser_read_page", parameters={"url": url, "method": "GET"}, external_network=external_network_enabled())
    if decision["decision"] == "DENIED":
        return advisory_envelope(schema="browser-read-denied", decision=decision, url=redact_secrets(url))
    return browser_fetch_page(url=url)


def browser_extract_text(*, url: str) -> dict[str, Any]:
    page = browser_read_page(url=url)
    text = page.get("plain_text") or page.get("text_preview") or ""
    return advisory_envelope(
        schema="browser-extract-text",
        url=url,
        text=text[:4000],
        source_schema=page.get("schema"),
        live_fetch=page.get("live_fetch", False),
        is_proof=False,
    )


def browser_screenshot(*, url: str) -> dict[str, Any]:
    page = browser_read_page(url=url)
    if page.get("schema") in {"browser-read-denied", "browser-read-error", "browser-open-denied"}:
        return advisory_envelope(schema="browser-screenshot", captured=False, url=url, detail=page.get("schema"))
    BROWSER_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", url)[:60]
    artifact = BROWSER_ARTIFACT_DIR / f"{stamp}_{safe}.html"
    snippet = page.get("text_preview", "")[:8000]
    artifact.write_text(f"<!-- url={url} -->\n{snippet}", encoding="utf-8")
    return advisory_envelope(
        schema="browser-screenshot",
        captured=True,
        url=url,
        artifact_ref=str(artifact.relative_to(WORKSPACE)),
        live_fetch=page.get("live_fetch", False),
        live_side_effect=False,
    )


def browser_search_public_web_request(*, query: str) -> dict[str, Any]:
    if live_browser_allowed():
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        return browser_open_url_request(url=url, method="GET")
    return browser_open_url_request(url=f"fixture://search?q={query}")


def browser_form_detect(*, html: str = "") -> dict[str, Any]:
    risks = _detect_risks(html)
    decision = "FULL_STOP" if any(risks.values()) else "AUTO_APPROVE"
    return advisory_envelope(schema="browser-form-detect", risks=risks, decision=decision, live_side_effect=False)


def browser_form_submit(*, url: str) -> dict[str, Any]:
    return advisory_envelope(
        schema="browser-form-submit-denied",
        url=url,
        decision="FULL_STOP",
        explanation="Form submit forbidden by default",
        live_side_effect=False,
    )


def execute_browser_tool(tool_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    if tool_id == "browser_open_url_request":
        return browser_open_url_request(url=str(parameters.get("url", "fixture://local")), method=str(parameters.get("method", "GET")))
    if tool_id == "browser_read_page":
        url = str(parameters.get("url", LIVE_TEST_URL if live_browser_allowed() else "fixture://local"))
        return browser_read_page(url=url)
    if tool_id == "browser_extract_text":
        url = str(parameters.get("url", LIVE_TEST_URL if live_browser_allowed() else "fixture://local"))
        return browser_extract_text(url=url)
    if tool_id == "browser_screenshot":
        url = str(parameters.get("url", LIVE_TEST_URL if live_browser_allowed() else "fixture://local"))
        return browser_screenshot(url=url)
    if tool_id == "browser_search_public_web_request":
        return browser_search_public_web_request(query=str(parameters.get("query", "hydrogenuine")))
    if tool_id == "browser_form_detect":
        return browser_form_detect(html=str(parameters.get("html", "")))
    if tool_id == "browser_login_detect":
        return browser_form_detect(html=str(parameters.get("html", "login password")))
    if tool_id == "browser_account_creation_detect":
        return browser_form_detect(html=str(parameters.get("html", "create account sign up")))
    if tool_id in {"browser_follow_link_request", "browser_download_request"}:
        lattice = ApprovalDecisionEngine().evaluate(action_id=tool_id, external_network=external_network_enabled())
        return advisory_envelope(schema="browser-action-review", tool_id=tool_id, lattice=lattice)
    if tool_id == "browser_form_submit":
        return browser_form_submit(url=str(parameters.get("url", "")))
    return advisory_envelope(schema="browser-unknown", tool_id=tool_id)


__all__ = [
    "BROWSER_ARTIFACT_DIR",
    "LIVE_TEST_URL",
    "browser_extract_text",
    "browser_fetch_page",
    "browser_form_submit",
    "browser_open_url_request",
    "browser_read_fixture",
    "browser_read_page",
    "browser_screenshot",
    "execute_browser_tool",
    "external_network_enabled",
    "live_browser_allowed",
]
