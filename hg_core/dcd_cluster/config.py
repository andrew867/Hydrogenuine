"""DCD cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def dcd_enabled() -> bool:
    return _flag("HG_DCD_ENABLED", default="0")


def dcd_static_fixtures_only() -> bool:
    return _flag("HG_DCD_STATIC_FIXTURES_ONLY", default="1")


def dcd_refuse_authority_conversion() -> bool:
    return _flag("HG_DCD_REFUSE_AUTHORITY_CONVERSION", default="1")


def dcd_refuse_live_model_invocation() -> bool:
    return _flag("HG_DCD_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "dcd_enabled",
    "dcd_refuse_authority_conversion",
    "dcd_refuse_live_model_invocation",
    "dcd_static_fixtures_only",
]

