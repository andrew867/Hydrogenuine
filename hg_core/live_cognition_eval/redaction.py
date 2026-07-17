"""Transcript redaction and artifact policy (CT-13 LCB)."""

from __future__ import annotations

import re
from typing import Any

_SECRET_KEY_FRAGMENTS = ("api_key", "apikey", "token", "secret", "password", "authorization")
_SK_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def redact_transcript(value: Any) -> Any:
    """Redact secret-like fields from eval transcripts and gate artifacts."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_transcript(item)
        return out
    if isinstance(value, list):
        return [redact_transcript(item) for item in value]
    if isinstance(value, str):
        if value.startswith("sk-"):
            return "[REDACTED]"
        return _SK_PATTERN.sub("[REDACTED]", value)
    return value


def transcript_artifact_policy(*, partial_stream: bool = False) -> dict[str, Any]:
  return {
      "artifact_tier": "temporary" if partial_stream else "archivable",
      "redaction_required": True,
      "world_state_eligible": False,
      "authority_eligible": False,
      "notes": (
          "Partial-stream transcripts are quarantined as temporary and never enter world state."
          if partial_stream
          else "Completed eval transcripts are evidence only; model output is non-authoritative."
      ),
  }


__all__ = ["redact_transcript", "transcript_artifact_policy"]
