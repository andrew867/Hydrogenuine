"""IMB cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def imb_enabled() -> bool:
    return _flag("HG_IMB_ENABLED", default="0")


def imb_static_fixtures_only() -> bool:
    return _flag("HG_IMB_STATIC_FIXTURES_ONLY", default="1")


def imb_refuse_stale_policy() -> bool:
    return _flag("HG_IMB_REFUSE_STALE_POLICY", default="1")


def imb_refuse_authority_conversion() -> bool:
    return _flag("HG_IMB_REFUSE_AUTHORITY_CONVERSION", default="1")


__all__ = [
    "imb_enabled",
    "imb_refuse_authority_conversion",
    "imb_refuse_stale_policy",
    "imb_static_fixtures_only",
]
