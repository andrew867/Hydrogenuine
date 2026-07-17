"""
Pack3 Phase 3: Tool abuse resistance — SSRF guard, allowlist, BlockedAction.

- SSRF: block link-local, RFC1918, metadata IPs, localhost; block file://, gopher://.
- Allowlist: tool must be in registry (caller enforces); optional magnification required_controls.
- Policy denials return BlockedAction (reason, code, details) for "why blocked" UI.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class BlockedAction:
    """Structured 'why blocked' returned to UI when policy denies a tool request."""
    reason: str
    code: str  # e.g. ssrf_blocked, tool_not_allowed
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"reason": self.reason, "code": self.code}
        if self.details:
            d["details"] = self.details
        return d


# Keys in tool inputs that may contain URLs or hosts (for SSRF check).
_URL_OR_HOST_KEYS = frozenset({
    "url", "base_url", "endpoint", "link", "href", "uri", "host",
    "base", "api_url", "server", "target", "redirect_uri",
})


def _normalize_for_ssrf(value: Any) -> Optional[str]:
    """Return a string host or URL to check, or None if not applicable."""
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s if s else None
    return None


def _is_blocked_scheme(url: str) -> bool:
    """Block file://, gopher://, and other non-http(s) schemes that can be abused."""
    lower = url.strip().lower()
    if "://" in lower:
        scheme = lower.split("://", 1)[0]
        if scheme in ("file", "gopher", "ftp", "data", "javascript"):
            return True
    return False


def _host_from_url(url: str) -> Optional[str]:
    """Extract host from URL string for IP checks."""
    url = url.strip()
    if not url:
        return None
    if "://" not in url:
        # Treat as hostname or IP (IPv6 can be "::1" so take part before first / only)
        return url.split("/")[0].strip() or None
    try:
        parsed = urlparse(url if url.startswith("http") else "https://" + url)
        return parsed.hostname or (parsed.netloc.split(":")[0] if parsed.netloc else None)
    except Exception:
        return url.split("/")[0].split(":")[0]


def _is_blocked_ip(host: str) -> bool:
    """True if host is localhost, link-local, RFC1918, or metadata."""
    host = host.strip().lower()
    if host in ("localhost", "localhost.", "::1"):
        return True
    # IPv4
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            return True
        if ip.is_link_local:
            return True
        if ip.is_private:
            return True
        # Metadata (e.g. cloud)
        if host == "169.254.169.254" or host.startswith("169.254."):
            return True
        return False
    except ValueError:
        pass
    # IPv6
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            return True
        if ip.is_link_local:
            return True
        if ip.is_private:
            return True
        return False
    except ValueError:
        pass
    # Hostname that looks like metadata
    if "metadata" in host or host == "169.254.169.254":
        return True
    return False


def check_ssrf(url_or_host: str) -> Optional[BlockedAction]:
    """
    Check a single URL or host for SSRF. Returns BlockedAction if blocked, else None.
    Blocks: localhost, 127.0.0.1, ::1, 169.254.x.x, 10.x, 172.16-31.x, 192.168.x,
    file://, gopher://, etc.
    """
    if not url_or_host or not isinstance(url_or_host, str):
        return None
    s = url_or_host.strip()
    if not s:
        return None
    if _is_blocked_scheme(s):
        return BlockedAction(
            reason="Blocked scheme (e.g. file://, gopher://) not allowed for tool requests.",
            code="ssrf_blocked",
            details={"value": "[REDACTED]", "scheme": s.split("://", 1)[0].lower() if "://" in s else None},
        )
    host = _host_from_url(s)
    if not host:
        return None
    if _is_blocked_ip(host):
        return BlockedAction(
            reason="Blocked host (localhost, private, or metadata).",
            code="ssrf_blocked",
            details={"host_type": "private_or_metadata"},
        )
    return None


def extract_url_candidates(inputs: Dict[str, Any]) -> List[str]:
    """Collect string values from input keys that typically hold URLs or hosts."""
    if not inputs or not isinstance(inputs, dict):
        return []
    out: List[str] = []
    for key, val in inputs.items():
        if key.lower() in _URL_OR_HOST_KEYS or "url" in key.lower() or "host" in key.lower():
            v = _normalize_for_ssrf(val)
            if v:
                out.append(v)
    return out


def check_request(
    tool_name: str,
    inputs: Dict[str, Any],
    tool_descriptor: Optional[Dict[str, Any]] = None,
    magnification_report: Optional[Dict[str, Any]] = None,
) -> Optional[BlockedAction]:
    """
    Run SSRF and allowlist checks. Returns BlockedAction if request should be denied, else None.
    - SSRF: any URL/host in inputs must pass check_ssrf.
    - Allowlist: tool_descriptor presence is enforced by caller (404); optional future: role/tags.
    """
    inputs = inputs or {}
    for candidate in extract_url_candidates(inputs):
        blocked = check_ssrf(candidate)
        if blocked:
            return blocked
    return None
