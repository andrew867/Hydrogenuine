"""ERB cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def erb_enabled() -> bool:
    return _flag("HG_ERB_ENABLED", default="0")


def erb_static_fixtures_only() -> bool:
    return _flag("HG_ERB_STATIC_FIXTURES_ONLY", default="1")


def erb_refuse_stale_policy() -> bool:
    return _flag("HG_ERB_REFUSE_STALE_POLICY", default="1")


def erb_refuse_authority_conversion() -> bool:
    return _flag("HG_ERB_REFUSE_AUTHORITY_CONVERSION", default="1")


__all__ = [
    "erb_enabled",
    "erb_refuse_authority_conversion",
    "erb_refuse_stale_policy",
    "erb_static_fixtures_only",
]
