"""EGI cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def egi_enabled() -> bool:
    return _flag("HG_EGI_ENABLED", default="0")


def egi_static_fixtures_only() -> bool:
    return _flag("HG_EGI_STATIC_FIXTURES_ONLY", default="1")


def egi_refuse_stale_approval() -> bool:
    return _flag("HG_EGI_REFUSE_STALE_APPROVAL", default="1")


def egi_refuse_authority_conversion() -> bool:
    return _flag("HG_EGI_REFUSE_AUTHORITY_CONVERSION", default="1")


__all__ = [
    "egi_enabled",
    "egi_refuse_authority_conversion",
    "egi_refuse_stale_approval",
    "egi_static_fixtures_only",
]
