"""EXCITON cluster feature flags — backburner by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def exciton_enabled() -> bool:
    return _flag("HG_EXCITON_ENABLED", default="0")


def exciton_backburner_guard() -> bool:
    return _flag("HG_EXCITON_BACKBURNER", default="1")


def exciton_native_ui_allowed() -> bool:
    return _flag("HG_EXCITON_NATIVE_UI_ALLOWED", default="0")


def exciton_static_fixtures_only() -> bool:
    return _flag("HG_EXCITON_STATIC_FIXTURES_ONLY", default="1")


def exciton_refuse_stale_approval() -> bool:
    return _flag("HG_EXCITON_REFUSE_STALE_APPROVAL", default="1")


def exciton_refuse_authority_conversion() -> bool:
    return _flag("HG_EXCITON_REFUSE_AUTHORITY_CONVERSION", default="1")


def exciton_fake_dispatch_only() -> bool:
    return _flag("HG_EXCITON_FAKE_DISPATCH_ONLY", default="1")


__all__ = [
    "exciton_backburner_guard",
    "exciton_enabled",
    "exciton_fake_dispatch_only",
    "exciton_native_ui_allowed",
    "exciton_refuse_authority_conversion",
    "exciton_refuse_stale_approval",
    "exciton_static_fixtures_only",
]
