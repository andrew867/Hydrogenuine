"""IPB cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def ipb_enabled() -> bool:
    return _flag("HG_IPB_ENABLED", default="0")


def ipb_static_fixtures_only() -> bool:
    return _flag("HG_IPB_STATIC_FIXTURES_ONLY", default="1")


def ipb_refuse_stale_envelope() -> bool:
    return _flag("HG_IPB_REFUSE_STALE_ENVELOPE", default="1")


def ipb_refuse_authority_conversion() -> bool:
    return _flag("HG_IPB_REFUSE_AUTHORITY_CONVERSION", default="1")


def ipb_fake_dispatch_only() -> bool:
    return _flag("HG_IPB_FAKE_DISPATCH_ONLY", default="1")


__all__ = [
    "ipb_enabled",
    "ipb_fake_dispatch_only",
    "ipb_refuse_authority_conversion",
    "ipb_refuse_stale_envelope",
    "ipb_static_fixtures_only",
]
