"""Crash log redaction before write (CT-02)."""

from __future__ import annotations

import traceback
from typing import Mapping

from hg_core.secrets.redact import redact_payload, redact_text


def format_crash_report(
    exc: BaseException,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    """Format exception + redacted env for crash logs."""
    lines = [
        f"exception: {type(exc).__name__}",
        f"message: {redact_text(str(exc))[0]}",
        "traceback:",
        redact_text(traceback.format_exc())[0],
    ]
    if env:
        safe_env = redact_payload(dict(env))
        lines.append(f"env_redacted: {safe_env}")
    return "\n".join(lines)


__all__ = ["format_crash_report"]
