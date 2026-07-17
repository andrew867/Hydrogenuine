"""DAB cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def dab_enabled() -> bool:
    return _flag("HG_DAB_ENABLED", default="0")


def dab_static_fixtures_only() -> bool:
    return _flag("HG_DAB_STATIC_FIXTURES_ONLY", default="1")


def dab_refuse_authority_conversion() -> bool:
    return _flag("HG_DAB_REFUSE_AUTHORITY_CONVERSION", default="1")


def dab_refuse_live_model_invocation() -> bool:
    return _flag("HG_DAB_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "dab_enabled",
    "dab_refuse_authority_conversion",
    "dab_refuse_live_model_invocation",
    "dab_static_fixtures_only",
]

