"""ORI cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def ori_enabled() -> bool:
    return _flag("HG_ORI_ENABLED", default="0")


def ori_static_fixtures_only() -> bool:
    return _flag("HG_ORI_STATIC_FIXTURES_ONLY", default="1")


def ori_refuse_stale_review() -> bool:
    return _flag("HG_ORI_REFUSE_STALE_REVIEW", default="1")


def ori_refuse_authority_conversion() -> bool:
    return _flag("HG_ORI_REFUSE_AUTHORITY_CONVERSION", default="1")


__all__ = [
    "ori_enabled",
    "ori_refuse_authority_conversion",
    "ori_refuse_stale_review",
    "ori_static_fixtures_only",
]
