"""AIS cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def ais_enabled() -> bool:
    return _flag("HG_AIS_ENABLED", default="0")


def ais_static_fixtures_only() -> bool:
    return _flag("HG_AIS_STATIC_FIXTURES_ONLY", default="1")


def ais_refuse_authority_conversion() -> bool:
    return _flag("HG_AIS_REFUSE_AUTHORITY_CONVERSION", default="1")


def ais_refuse_live_model_invocation() -> bool:
    return _flag("HG_AIS_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "ais_enabled",
    "ais_refuse_authority_conversion",
    "ais_refuse_live_model_invocation",
    "ais_static_fixtures_only",
]
