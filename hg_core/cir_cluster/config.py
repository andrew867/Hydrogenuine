"""CIR cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def cir_enabled() -> bool:
    return _flag("HG_CIR_ENABLED", default="0")


def cir_static_fixtures_only() -> bool:
    return _flag("HG_CIR_STATIC_FIXTURES_ONLY", default="1")


def cir_refuse_authority_conversion() -> bool:
    return _flag("HG_CIR_REFUSE_AUTHORITY_CONVERSION", default="1")


def cir_refuse_live_model_invocation() -> bool:
    return _flag("HG_CIR_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "cir_enabled",
    "cir_refuse_authority_conversion",
    "cir_refuse_live_model_invocation",
    "cir_static_fixtures_only",
]
