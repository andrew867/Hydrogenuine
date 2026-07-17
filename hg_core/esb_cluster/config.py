"""ESB cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def esb_enabled() -> bool:
    return _flag("HG_ESB_ENABLED", default="0")


def esb_static_fixtures_only() -> bool:
    return _flag("HG_ESB_STATIC_FIXTURES_ONLY", default="1")


def esb_refuse_authority_conversion() -> bool:
    return _flag("HG_ESB_REFUSE_AUTHORITY_CONVERSION", default="1")


def esb_refuse_live_model_invocation() -> bool:
    return _flag("HG_ESB_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "esb_enabled",
    "esb_refuse_authority_conversion",
    "esb_refuse_live_model_invocation",
    "esb_static_fixtures_only",
]
