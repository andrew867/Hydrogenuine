"""
Redaction for logs and SSE. Delegates to hg_core.security.redaction (Pack3).
"""

from typing import Any, Set

from hg_core.security.redaction import SENSITIVE_KEYS, redact_json

__all__ = ["SENSITIVE_KEYS", "redact_sensitive"]


def redact_sensitive(payload: Any, keys: Set[str] | None = None) -> Any:
    """
    Return a copy of payload with values for sensitive keys replaced by [REDACTED].
    Backward-compatible wrapper around hg_core.security.redaction.redact_json.
    """
    return redact_json(payload, sensitive_keys=keys or SENSITIVE_KEYS)
