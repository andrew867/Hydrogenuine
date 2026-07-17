"""A0-HM cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def a0_hm_enabled() -> bool:
    return _flag("HG_A0_HM_ENABLED", default="0")


def a0_hm_static_fixtures_only() -> bool:
    return _flag("HG_A0_HM_STATIC_FIXTURES_ONLY", default="1")


def a0_hm_refuse_authority_conversion() -> bool:
    return _flag("HG_A0_HM_REFUSE_AUTHORITY_CONVERSION", default="1")


def a0_hm_refuse_spiritual_as_proof() -> bool:
    return _flag("HG_A0_HM_REFUSE_SPIRITUAL_AS_PROOF", default="1")


__all__ = [
    "a0_hm_enabled",
    "a0_hm_refuse_authority_conversion",
    "a0_hm_refuse_spiritual_as_proof",
    "a0_hm_static_fixtures_only",
]
