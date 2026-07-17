"""Dashboard-specific redaction. Re-exports from demo_bundle.redaction."""

from __future__ import annotations

from hg_runtime.demo_bundle.redaction import (
    redact_path,
    redact_text,
    redact_endpoint,
    redact_json_values,
)

__all__ = ["redact_path", "redact_text", "redact_endpoint", "redact_json_values"]
