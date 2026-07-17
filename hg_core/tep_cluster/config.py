"""TEP cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def tep_enabled() -> bool:
    return _flag("HG_TEP_ENABLED", default="0")


def tep_static_fixtures_only() -> bool:
    return _flag("HG_TEP_STATIC_FIXTURES_ONLY", default="1")


def tep_refuse_authority_conversion() -> bool:
    return _flag("HG_TEP_REFUSE_AUTHORITY_CONVERSION", default="1")


def tep_refuse_naked_claims() -> bool:
    return _flag("HG_TEP_REFUSE_NAKED_CLAIMS", default="1")


__all__ = [
    "tep_enabled",
    "tep_refuse_authority_conversion",
    "tep_refuse_naked_claims",
    "tep_static_fixtures_only",
]
