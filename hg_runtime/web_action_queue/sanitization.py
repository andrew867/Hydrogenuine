"""Sanitization for web actions — no secrets, cookies, or session data."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from hg_runtime.web_action_queue.errors import WebCargoAuthorizesError, WebSecretExposureError

_TOKEN_QUERY_KEYS = frozenset(
    {"token", "access_token", "session", "sessionid", "auth", "key", "api_key", "password", "secret"}
)
_SECRET_PATTERNS = (
    re.compile(r"Bearer\s+\S+", re.I),
    re.compile(r"Set-Cookie:\s*", re.I),
    re.compile(r"sessionid=\S+", re.I),
)
_INJECTION_MARKERS = (
    "ignore previous instructions",
    "you must approve",
    "auto-approve this",
    "grant permission",
    "execute immediately",
    "system:",
    "operator instruction:",
)
_AUTHORIZE_MARKERS = (
    "you are now authorized",
    "permission granted",
    "approve this action",
    "this page authorizes",
)


def _frozen_false() -> dict:
    return {"advisory_only": True, "permission_granted": False, "authority_created": False}


class WebActionSanitizer:
    """Scrub URLs, previews, and cargo for safe display."""

    @staticmethod
    def redact_url(url: str | None) -> str | None:
        if not url:
            return None
        try:
            parsed = urlparse(url)
            if parsed.query:
                pairs = []
                for part in parsed.query.split("&"):
                    if "=" in part:
                        k, _v = part.split("=", 1)
                        if k.lower() in _TOKEN_QUERY_KEYS:
                            pairs.append(f"{k}=[REDACTED]")
                        else:
                            pairs.append(part)
                    else:
                        pairs.append(part)
                query = "&".join(pairs)
            else:
                query = ""
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, ""))
        except ValueError:
            return url.split("?")[0][:200]

    @staticmethod
    def sanitize_preview(text: str) -> str:
        out = text
        for pat in _SECRET_PATTERNS:
            out = pat.sub("[REDACTED]", out)
        for key in ("cookie", "session", "authorization", "password", "credential"):
            if key in out.lower():
                out = re.sub(rf"{key}[=:]\S+", f"{key}=[REDACTED]", out, flags=re.I)
        return out[:2000]

    @staticmethod
    def summarize_form_fields(fields: dict[str, str] | None) -> str | None:
        if not fields:
            return None
        parts = []
        for k in sorted(fields.keys()):
            parts.append(f"{k}=[REDACTED]")
        return "; ".join(parts)[:500]

    @staticmethod
    def detect_prompt_injection(cargo_text: str | None) -> bool:
        if not cargo_text:
            return False
        lower = cargo_text.lower()
        return any(m in lower for m in _INJECTION_MARKERS)

    @staticmethod
    def detect_cargo_authorizes(cargo_text: str | None) -> bool:
        if not cargo_text:
            return False
        lower = cargo_text.lower()
        return any(m in lower for m in _AUTHORIZE_MARKERS)

    @staticmethod
    def validate_no_secrets(payload: dict) -> None:
        text = str(payload).lower()
        if "set-cookie" in text or "sessionid=" in text:
            raise WebSecretExposureError("cookie/session data in payload")
        for pat in _SECRET_PATTERNS:
            if pat.search(str(payload)):
                raise WebSecretExposureError("secret pattern in payload")

    @staticmethod
    def validate_cargo_not_command(cargo_text: str | None) -> None:
        if WebActionSanitizer.detect_cargo_authorizes(cargo_text):
            raise WebCargoAuthorizesError("page content cannot authorize actions")


__all__ = ["WebActionSanitizer"]
