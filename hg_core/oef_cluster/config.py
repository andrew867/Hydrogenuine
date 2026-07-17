"""OEF cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def oef_enabled() -> bool:
    return _flag("HG_OEF_ENABLED", default="0")


def oef_static_fixtures_only() -> bool:
    return _flag("HG_OEF_STATIC_FIXTURES_ONLY", default="1")


def oef_refuse_authority_conversion() -> bool:
    return _flag("HG_OEF_REFUSE_AUTHORITY_CONVERSION", default="1")


def oef_refuse_live_model_invocation() -> bool:
    return _flag("HG_OEF_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "oef_enabled",
    "oef_refuse_authority_conversion",
    "oef_refuse_live_model_invocation",
    "oef_static_fixtures_only",
]
