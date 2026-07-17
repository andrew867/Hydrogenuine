"""H8 cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def h8_enabled() -> bool:
    return _flag("HG_H8_ENABLED", default="0")


def h8_static_fixtures_only() -> bool:
    return _flag("HG_H8_STATIC_FIXTURES_ONLY", default="1")


def h8_refuse_authority_conversion() -> bool:
    return _flag("HG_H8_REFUSE_AUTHORITY_CONVERSION", default="1")


def h8_refuse_live_model_invocation() -> bool:
    return _flag("HG_H8_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "h8_enabled",
    "h8_refuse_authority_conversion",
    "h8_refuse_live_model_invocation",
    "h8_static_fixtures_only",
]
