"""REB cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def reb_enabled() -> bool:
    return _flag("HG_REB_ENABLED", default="0")


def reb_static_fixtures_only() -> bool:
    return _flag("HG_REB_STATIC_FIXTURES_ONLY", default="1")


def reb_refuse_stale_reentry_request() -> bool:
    return _flag("HG_REB_REFUSE_STALE_REENTRY_REQUEST", default="1")


def reb_refuse_authority_conversion() -> bool:
    return _flag("HG_REB_REFUSE_AUTHORITY_CONVERSION", default="1")


def reb_fake_dispatch_only() -> bool:
    return _flag("HG_REB_FAKE_DISPATCH_ONLY", default="1")


__all__ = [
    "reb_enabled",
    "reb_fake_dispatch_only",
    "reb_refuse_authority_conversion",
    "reb_refuse_stale_reentry_request",
    "reb_static_fixtures_only",
]
