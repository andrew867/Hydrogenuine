"""BRS cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def brs_enabled() -> bool:
    return _flag("HG_BRS_ENABLED", default="0")


def brs_static_fixtures_only() -> bool:
    return _flag("HG_BRS_STATIC_FIXTURES_ONLY", default="1")


def brs_refuse_authority_conversion() -> bool:
    return _flag("HG_BRS_REFUSE_AUTHORITY_CONVERSION", default="1")


def brs_refuse_live_model_invocation() -> bool:
    return _flag("HG_BRS_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "brs_enabled",
    "brs_refuse_authority_conversion",
    "brs_refuse_live_model_invocation",
    "brs_static_fixtures_only",
]
