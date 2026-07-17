"""
Central redaction for logs, SSE, audit, and run bundles (Pack3).

Use redact_text() for free-form text (API keys, bearer tokens, common secret shapes).
Use redact_json() for structured payloads with configurable sensitive keys.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Union

# Default keys whose values are redacted in structured payloads (logs, SSE, audit)
SENSITIVE_KEYS: Set[str] = {
    "content",
    "payload",
    "note",
    "resolution_note",
    "summary",
    "summary_text",
    "key_facts",
    "conflicts",
    "message",
    "inputs",
    "outputs",
    "tool_payload",
    "tool_result",
    "secret",
    "api_key",
    "password",
    "token",
    "authorization",
}

# Patterns for redact_text (compiled once)
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE)
_API_KEY_LIKE = re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{10,}['\"]?", re.IGNORECASE)
_GENERIC_SECRET = re.compile(r"(?:secret|password|passwd)\s*[:=]\s*['\"]?[^'\"]+['\"]?", re.IGNORECASE)
_PLACEHOLDER = "[REDACTED]"


def redact_text(text: str, patterns: List[re.Pattern] | None = None) -> str:
    """
    Redact free-form text using default or custom patterns.
    Default: Bearer tokens, api_key=..., secret=..., password=...
    """
    if not text or not isinstance(text, str):
        return text
    pats = patterns or [_BEARER, _API_KEY_LIKE, _GENERIC_SECRET]
    out = text
    for p in pats:
        out = p.sub(_PLACEHOLDER, out)
    return out


def redact_json(
    payload: Any,
    sensitive_keys: Set[str] | None = None,
    keys_allowlist: Set[str] | None = None,
    keys_denylist: Set[str] | None = None,
) -> Any:
    """
    Return a copy of payload with values for sensitive keys replaced by [REDACTED].
    Recurses into dicts; list items are redacted if they are dicts.
    sensitive_keys: keys to redact (default SENSITIVE_KEYS).
    keys_allowlist: if set, only these keys are NOT redacted (others with default set are).
    keys_denylist: if set, these keys are always redacted in addition to sensitive_keys.
    """
    keys = sensitive_keys or SENSITIVE_KEYS
    if keys_denylist:
        keys = keys | keys_denylist
    if isinstance(payload, dict):
        out: Dict[str, Any] = {}
        for k, v in payload.items():
            if keys_allowlist is not None and k in keys_allowlist:
                out[k] = redact_json(v, sensitive_keys=keys, keys_allowlist=keys_allowlist, keys_denylist=None)
            elif k in keys:
                out[k] = _PLACEHOLDER
            else:
                out[k] = redact_json(v, sensitive_keys=keys, keys_allowlist=keys_allowlist, keys_denylist=None)
        return out
    if isinstance(payload, list):
        return [redact_json(item, sensitive_keys=keys, keys_allowlist=keys_allowlist, keys_denylist=None) for item in payload]
    return payload


def sensitive_fields_for_tool(tool_name: str) -> Set[str]:
    """
    Return the set of output field names that should be redacted for a given tool.
    Override via registry or config per tool; default is SENSITIVE_KEYS.
    """
    # Per-tool overrides can be added here or from a registry
    return SENSITIVE_KEYS
