"""ALC cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def alc_enabled() -> bool:
    return _flag("HG_ALC_ENABLED", default="0")


def alc_static_fixtures_only() -> bool:
    return _flag("HG_ALC_STATIC_FIXTURES_ONLY", default="1")


def alc_refuse_authority_conversion() -> bool:
    return _flag("HG_ALC_REFUSE_AUTHORITY_CONVERSION", default="1")


def alc_refuse_live_model_invocation() -> bool:
    return _flag("HG_ALC_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "alc_enabled",
    "alc_refuse_authority_conversion",
    "alc_refuse_live_model_invocation",
    "alc_static_fixtures_only",
]
