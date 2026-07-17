"""ISB cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def isb_enabled() -> bool:
    return _flag("HG_ISB_ENABLED", default="0")


def isb_static_fixtures_only() -> bool:
    return _flag("HG_ISB_STATIC_FIXTURES_ONLY", default="1")


def isb_refuse_authority_conversion() -> bool:
    return _flag("HG_ISB_REFUSE_AUTHORITY_CONVERSION", default="1")


def isb_refuse_live_model_invocation() -> bool:
    return _flag("HG_ISB_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "isb_enabled",
    "isb_refuse_authority_conversion",
    "isb_refuse_live_model_invocation",
    "isb_static_fixtures_only",
]
