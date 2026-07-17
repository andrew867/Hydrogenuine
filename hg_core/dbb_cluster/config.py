"""DBB cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def dbb_enabled() -> bool:
    return _flag("HG_DBB_ENABLED", default="0")


def dbb_static_fixtures_only() -> bool:
    return _flag("HG_DBB_STATIC_FIXTURES_ONLY", default="1")


def dbb_refuse_authority_conversion() -> bool:
    return _flag("HG_DBB_REFUSE_AUTHORITY_CONVERSION", default="1")


def dbb_refuse_live_model_invocation() -> bool:
    return _flag("HG_DBB_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "dbb_enabled",
    "dbb_refuse_authority_conversion",
    "dbb_refuse_live_model_invocation",
    "dbb_static_fixtures_only",
]
