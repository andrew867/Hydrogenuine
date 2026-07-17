"""RIB cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def rib_enabled() -> bool:
    return _flag("HG_RIB_ENABLED", default="0")


def rib_static_fixtures_only() -> bool:
    return _flag("HG_RIB_STATIC_FIXTURES_ONLY", default="1")


def rib_refuse_stale_spawn_request() -> bool:
    return _flag("HG_RIB_REFUSE_STALE_SPAWN_REQUEST", default="1")


def rib_refuse_authority_conversion() -> bool:
    return _flag("HG_RIB_REFUSE_AUTHORITY_CONVERSION", default="1")


def rib_fake_dispatch_only() -> bool:
    return _flag("HG_RIB_FAKE_DISPATCH_ONLY", default="1")


__all__ = [
    "rib_enabled",
    "rib_fake_dispatch_only",
    "rib_refuse_authority_conversion",
    "rib_refuse_stale_spawn_request",
    "rib_static_fixtures_only",
]
