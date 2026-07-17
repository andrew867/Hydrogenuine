"""HRT cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def hrt_enabled() -> bool:
    return _flag("HG_HRT_ENABLED", default="0")


def hrt_static_fixtures_only() -> bool:
    return _flag("HG_HRT_STATIC_FIXTURES_ONLY", default="1")


def hrt_refuse_authority_conversion() -> bool:
    return _flag("HG_HRT_REFUSE_AUTHORITY_CONVERSION", default="1")


def hrt_refuse_live_model_invocation() -> bool:
    return _flag("HG_HRT_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "hrt_enabled",
    "hrt_refuse_authority_conversion",
    "hrt_refuse_live_model_invocation",
    "hrt_static_fixtures_only",
]
