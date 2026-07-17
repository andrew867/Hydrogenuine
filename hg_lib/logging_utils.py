"""
Centralized logging for Hydrogenuine. Injects run_id, job_id, platform, mode.
"""

import logging
import os
from typing import Any

# Module-level context for log injection
_log_context: dict[str, str] = {}


def configure_logging(
    level: str | None = None,
    json: bool = False,
    run_id: str | None = None,
    job_id: str | None = None,
    platform: str | None = None,
    mode: str | None = None,
) -> None:
    """
    Configure root logger. Store context for injection into log records.
    """
    log_level = level or os.environ.get("HG_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    global _log_context
    _log_context.clear()
    if run_id is not None:
        _log_context["run_id"] = str(run_id)
    if job_id is not None:
        _log_context["job_id"] = str(job_id)
    if platform is not None:
        _log_context["platform"] = str(platform)
    if mode is not None:
        _log_context["mode"] = str(mode)


def get_log_context() -> dict[str, str]:
    """Return current log context for use in extra= parameter."""
    return dict(_log_context)


def set_log_context(**kwargs: str) -> None:
    """Update log context (merge into existing)."""
    global _log_context
    _log_context.update({k: str(v) for k, v in kwargs.items() if v is not None})
