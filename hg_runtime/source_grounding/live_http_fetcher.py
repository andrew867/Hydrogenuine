"""Live read-only HTTP GET fetcher for source retrieval.

GET-only.  No POST.  No login.  No form submission.  No side effects.
Source is not truth.  Retrieved text is not knowledge.
HTTP 200 is not authorization.  URL reachability is not permission.
"""

from __future__ import annotations

import hashlib
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from hg_runtime.source_grounding.read_only_web_retriever import (
    ALLOWED_FETCH_METHODS,
    is_url_safe_for_read,
)
from hg_runtime.reliability_tranche.integration import check_stop_panic

SCHEMA_VERSION = "live_http_fetch_receipt_v1"

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB cap

_DEFAULT_USER_AGENT = "HydrogenuineResearchBot/0.1 (read-only; no-login; no-post)"

_CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

USER_AGENT_PRESETS = {
    "default": _DEFAULT_USER_AGENT,
    "chrome": _CHROME_USER_AGENT,
}

_ACCESS_STATUS_MAP = {
    200: "public",
    403: "blocked",
    401: "blocked",
    402: "paywalled_preview",
    451: "blocked",
}


class _TextExtractor(HTMLParser):
    """Minimal HTML-to-text extractor."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False
        self._skip_tags = frozenset({"script", "style", "noscript"})

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def get_text(self) -> str:
        return "\n".join(self._chunks)


def _extract_text_from_html(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


def _classify_access(status: int, content: str) -> str:
    if status in _ACCESS_STATUS_MAP:
        return _ACCESS_STATUS_MAP[status]
    if status >= 400:
        return "failed"
    lower = content[:2000].lower() if content else ""
    if "abstract" in lower and ("full text" in lower or "subscribe" in lower):
        return "abstract_only"
    return "public"


def fetch_readonly_get(
    *,
    url: str,
    source_candidate_id: str = "",
    timeout_seconds: int = 20,
    stop_file: str = "",
    panic_file: str = "",
    user_agent: str = "",
    user_agent_preset: str = "",
) -> dict:
    """Perform a single read-only HTTP GET and return a receipt.

    No POST.  No login.  No form submission.  No side effects.
    Failures are returned as receipts, not raised as exceptions.
    """
    started = datetime.now(timezone.utc)

    resolved_preset = user_agent_preset or ("default" if not user_agent else "")
    resolved_ua = user_agent or USER_AGENT_PRESETS.get(resolved_preset, _DEFAULT_USER_AGENT)

    receipt: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "source_candidate_id": source_candidate_id,
        "canonical_url": url.split("?")[0].split("#")[0],
        "url": url,
        "retrieval_mode": "read_only",
        "retrieval_backend": "live_http_get",
        "http_method": "GET",
        "http_status": 0,
        "content_type": "",
        "content_hash": "",
        "content_length": 0,
        "text_extract": "",
        "text_extract_path": "",
        "access_status": "unknown",
        "fetch_started_at": started.isoformat(),
        "fetch_completed_at": "",
        "timeout_seconds": timeout_seconds,
        "success": False,
        "failure_reason": "",
        "error_type": "",
        "error_message": "",
        "external_effects_attempted": False,
        "login_attempted": False,
        "form_submit_attempted": False,
        "post_attempted": False,
        "promotion_allowed": False,
        "operator_review_required": True,
        "source_is_truth": False,
        "screenshot_is_truth": False,
        "user_agent_used": resolved_ua,
        "user_agent_preset": resolved_preset,
        "user_agent_reason": "compatibility",
        "access_bypass_attempted": False,
        "paywall_bypass_attempted": False,
        "notes": "",
    }

    if stop_file or panic_file:
        sp = check_stop_panic(stop_file=stop_file, panic_file=panic_file)
        if sp["active"]:
            receipt["access_status"] = "blocked"
            receipt["failure_reason"] = f"stop_panic: {sp['reason']}"
            receipt["error_type"] = "stop_panic"
            receipt["error_message"] = sp["reason"]
            receipt["fetch_completed_at"] = datetime.now(timezone.utc).isoformat()
            return receipt

    safe, reason = is_url_safe_for_read(url)
    if not safe:
        receipt["access_status"] = "blocked"
        receipt["failure_reason"] = reason
        receipt["error_type"] = "blocked_url"
        receipt["error_message"] = reason
        receipt["fetch_completed_at"] = datetime.now(timezone.utc).isoformat()
        return receipt

    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "User-Agent": resolved_ua,
                "Accept": "text/html,application/xhtml+xml,text/plain",
            },
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout_seconds, context=ctx) as resp:
            final_url = resp.url if hasattr(resp, "url") else url
            redirect_safe, redirect_reason = is_url_safe_for_read(final_url)
            if not redirect_safe:
                receipt["access_status"] = "blocked"
                receipt["failure_reason"] = f"redirect to blocked URL: {redirect_reason}"
                receipt["error_type"] = "blocked_redirect"
                receipt["error_message"] = f"redirected to {final_url}"
                receipt["login_attempted"] = False
                receipt["fetch_completed_at"] = datetime.now(timezone.utc).isoformat()
                return receipt

            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            raw_bytes = resp.read(_MAX_RESPONSE_BYTES)

        charset = "utf-8"
        ct_lower = content_type.lower()
        m = re.search(r"charset=([^\s;]+)", ct_lower)
        if m:
            charset = m.group(1)

        try:
            raw_text = raw_bytes.decode(charset, errors="replace")
        except (LookupError, UnicodeDecodeError):
            raw_text = raw_bytes.decode("utf-8", errors="replace")

        if "html" in ct_lower:
            text_extract = _extract_text_from_html(raw_text)
        else:
            text_extract = raw_text

        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        access_status = _classify_access(status, raw_text)

        receipt["http_status"] = status
        receipt["content_type"] = content_type
        receipt["content_hash"] = content_hash
        receipt["content_length"] = len(raw_bytes)
        receipt["text_extract"] = text_extract[:50000]
        receipt["access_status"] = access_status
        receipt["success"] = True

    except urllib.error.HTTPError as e:
        receipt["http_status"] = e.code
        receipt["access_status"] = _classify_access(e.code, "")
        receipt["failure_reason"] = str(e)
        receipt["error_type"] = "http_error"
        receipt["error_message"] = str(e)

    except urllib.error.URLError as e:
        receipt["access_status"] = "failed"
        receipt["failure_reason"] = str(e.reason)
        receipt["error_type"] = "url_error"
        receipt["error_message"] = str(e.reason)

    except TimeoutError:
        receipt["access_status"] = "failed"
        receipt["failure_reason"] = f"timeout after {timeout_seconds}s"
        receipt["error_type"] = "timeout"
        receipt["error_message"] = f"timeout after {timeout_seconds}s"

    except Exception as e:
        receipt["access_status"] = "failed"
        receipt["failure_reason"] = str(e)
        receipt["error_type"] = type(e).__name__
        receipt["error_message"] = str(e)

    receipt["fetch_completed_at"] = datetime.now(timezone.utc).isoformat()
    receipt_id_raw = (
        f"{receipt['canonical_url']}:{receipt['fetch_started_at']}"
    )
    receipt["receipt_id"] = hashlib.sha256(
        receipt_id_raw.encode()
    ).hexdigest()[:24]
    return receipt
