"""ARB cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def arb_enabled() -> bool:
    return _flag("HG_ARB_ENABLED", default="0")


def arb_static_fixtures_only() -> bool:
    return _flag("HG_ARB_STATIC_FIXTURES_ONLY", default="1")


def arb_refuse_stale_policy() -> bool:
    return _flag("HG_ARB_REFUSE_STALE_POLICY", default="1")


def arb_refuse_authority_conversion() -> bool:
    return _flag("HG_ARB_REFUSE_AUTHORITY_CONVERSION", default="1")


def arb_fake_dispatch_only() -> bool:
    return _flag("HG_ARB_FAKE_DISPATCH_ONLY", default="1")


__all__ = [
    "arb_enabled",
    "arb_fake_dispatch_only",
    "arb_refuse_authority_conversion",
    "arb_refuse_stale_policy",
    "arb_static_fixtures_only",
]
