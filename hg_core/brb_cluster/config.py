"""BRB cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def brb_enabled() -> bool:
    return _flag("HG_BRB_ENABLED", default="0")


def brb_static_fixtures_only() -> bool:
    return _flag("HG_BRB_STATIC_FIXTURES_ONLY", default="1")


def brb_refuse_authority_conversion() -> bool:
    return _flag("HG_BRB_REFUSE_AUTHORITY_CONVERSION", default="1")


def brb_refuse_live_model_invocation() -> bool:
    return _flag("HG_BRB_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "brb_enabled",
    "brb_refuse_authority_conversion",
    "brb_refuse_live_model_invocation",
    "brb_static_fixtures_only",
]

