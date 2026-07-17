"""Read-only web retriever — GET-only, no login, no POST, no side effects.

Source is not truth. Browser result is not truth. Retrieved text is not
knowledge. HTTP GET is not authorization. URL reachability is not permission.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

SCHEMA_VERSION = "web_retrieval_receipt_v2"

ALLOWED_FETCH_METHODS = frozenset({"GET", "HEAD", "PLAYWRIGHT_RENDER"})

FORBIDDEN_FETCH_METHODS = frozenset({
    "POST", "PUT", "PATCH", "DELETE", "OPTIONS_WRITE",
})

BLOCKED_URL_PATTERNS = [
    r"/login", r"/signin", r"/sign-in", r"/auth",
    r"/register", r"/signup", r"/sign-up",
    r"/checkout", r"/payment", r"/purchase",
    r"/comment", r"/reply", r"/post",
    r"/share", r"/send", r"/email",
    r"/upload", r"/submit",
]

_PRIVATE_HOSTNAME_SUFFIXES = (
    ".local", ".lan", ".internal", ".localhost",
)

_CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")


def _is_non_public_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True for private, loopback, link-local, reserved, CGNAT, etc."""
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
        or (isinstance(addr, ipaddress.IPv4Address) and addr in _CGNAT_NETWORK)
    )


def _is_private_or_local_host(hostname: str) -> bool:
    """Return True if hostname resolves to a private, loopback, link-local,
    CGNAT, or reserved IP address, or is a local/internal hostname."""
    if not hostname:
        return True
    lower = hostname.lower()
    if lower in ("localhost", "0.0.0.0", "[::]", "[::1]"):
        return True
    if lower.endswith(_PRIVATE_HOSTNAME_SUFFIXES):
        return True
    bare = lower.strip("[]")
    try:
        return _is_non_public_ip(ipaddress.ip_address(bare))
    except ValueError:
        pass
    host_no_port = bare.rsplit(":", 1)[0] if ":" in bare and not bare.startswith("[") else bare
    try:
        return _is_non_public_ip(ipaddress.ip_address(host_no_port))
    except ValueError:
        pass
    return False


def is_url_safe_for_read(url: str) -> tuple[bool, str]:
    lower = url.lower()
    for pattern in BLOCKED_URL_PATTERNS:
        if re.search(pattern, lower):
            return False, f"URL matches blocked pattern: {pattern}"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"unsupported scheme: {parsed.scheme}"
    if _is_private_or_local_host(parsed.hostname or ""):
        return False, f"private/local host blocked: {parsed.hostname}"
    return True, ""


def create_web_receipt(*, source_candidate_id: str, url: str,
                       canonical_url: str = "",
                       fetch_method: str = "GET",
                       http_status: int = 0,
                       content_type: str = "",
                       title: str = "",
                       author: str = "",
                       publisher: str = "",
                       publication_date: str = "",
                       access_status: str = "unknown",
                       content_text: str = "",
                       content_hash: str = "",
                       screenshot_hashes: list[str] | None = None,
                       text_extract_path: str = "",
                       screenshot_paths: list[str] | None = None,
                       network_request_summary_path: str = "",
                       extracted_claims_path: str = "",
                       unsupported_extrapolations_path: str = "",
                       boundary_audit_path: str = "",
                       success: bool = True,
                       failure_reason: str = "",
                       retrieval_method: str = "direct_url") -> dict:
    if fetch_method not in ALLOWED_FETCH_METHODS:
        raise ValueError(f"fetch method {fetch_method!r} not allowed")

    if not content_hash and content_text:
        content_hash = hashlib.sha256(content_text.encode()).hexdigest()

    receipt = {
        "schema": SCHEMA_VERSION,
        "receipt_id": "",
        "source_candidate_id": source_candidate_id,
        "url": url,
        "canonical_url": canonical_url or url.split("?")[0].split("#")[0],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "retrieval_method": retrieval_method,
        "fetch_method": fetch_method,
        "http_status": http_status,
        "content_type": content_type,
        "title": title,
        "author": author,
        "publisher": publisher,
        "publication_date": publication_date,
        "access_status": access_status,
        "content_hash": content_hash,
        "content_length": len(content_text),
        "screenshot_hashes": screenshot_hashes or [],
        "text_extract_path": text_extract_path,
        "screenshot_paths": screenshot_paths or [],
        "network_request_summary_path": network_request_summary_path,
        "extracted_claims_path": extracted_claims_path,
        "unsupported_extrapolations_path": unsupported_extrapolations_path,
        "boundary_audit_path": boundary_audit_path,
        "success": success,
        "failure_reason": failure_reason,
        "read_only_policy_enforced": True,
        "external_effects_attempted": False,
        "login_attempted": False,
        "form_submit_attempted": False,
        "post_attempted": False,
        "tool_authority_granted": False,
        "promotion_decision": "reject_pending_gate",
        "source_treated_as_truth": False,
        "grants_authority": False,
        "external_effect_created": False,
    }
    raw = json.dumps(receipt, sort_keys=True)
    receipt["receipt_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return receipt


def validate_web_receipt(receipt: dict) -> list[str]:
    errors = []
    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {receipt.get('schema')}")
    if receipt.get("source_treated_as_truth"):
        errors.append("source_treated_as_truth must be False")
    if receipt.get("grants_authority"):
        errors.append("grants_authority must be False")
    if receipt.get("external_effect_created"):
        errors.append("external_effect_created must be False")
    if receipt.get("external_effects_attempted"):
        errors.append("external_effects_attempted must be False")
    if receipt.get("login_attempted"):
        errors.append("login_attempted must be False")
    if receipt.get("form_submit_attempted"):
        errors.append("form_submit_attempted must be False")
    if receipt.get("post_attempted"):
        errors.append("post_attempted must be False")
    if receipt.get("tool_authority_granted"):
        errors.append("tool_authority_granted must be False")
    if not receipt.get("read_only_policy_enforced"):
        errors.append("read_only_policy_enforced must be True")
    if receipt.get("fetch_method") in FORBIDDEN_FETCH_METHODS:
        errors.append(f"forbidden fetch method: {receipt['fetch_method']}")
    return errors
