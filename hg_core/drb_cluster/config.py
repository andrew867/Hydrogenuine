"""DRB cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def drb_enabled() -> bool:
    return _flag("HG_DRB_ENABLED", default="0")


def drb_static_fixtures_only() -> bool:
    return _flag("HG_DRB_STATIC_FIXTURES_ONLY", default="1")


def drb_refuse_authority_conversion() -> bool:
    return _flag("HG_DRB_REFUSE_AUTHORITY_CONVERSION", default="1")


def drb_refuse_memory_mutation() -> bool:
    return _flag("HG_DRB_REFUSE_MEMORY_MUTATION", default="1")


def drb_refuse_live_model_invocation() -> bool:
    return _flag("HG_DRB_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "drb_enabled",
    "drb_refuse_authority_conversion",
    "drb_refuse_live_model_invocation",
    "drb_refuse_memory_mutation",
    "drb_static_fixtures_only",
]
