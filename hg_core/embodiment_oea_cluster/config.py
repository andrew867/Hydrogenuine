"""EOG cluster feature flags — backburner by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def eog_enabled() -> bool:
    return _flag("HG_EOG_ENABLED", default="0")


def eog_backburner_guard() -> bool:
    return _flag("HG_EOG_BACKBURNER", default="1")


def eog_hardware_allowed() -> bool:
    return _flag("HG_EOG_HARDWARE_ALLOWED", default="0")


def eog_static_fixtures_only() -> bool:
    return _flag("HG_EOG_STATIC_FIXTURES_ONLY", default="1")


def eog_refuse_stale_approval() -> bool:
    return _flag("HG_EOG_REFUSE_STALE_APPROVAL", default="1")


def eog_refuse_authority_conversion() -> bool:
    return _flag("HG_EOG_REFUSE_AUTHORITY_CONVERSION", default="1")


def eog_fake_dispatch_only() -> bool:
    return _flag("HG_EOG_FAKE_DISPATCH_ONLY", default="1")


__all__ = [
    "eog_backburner_guard",
    "eog_enabled",
    "eog_fake_dispatch_only",
    "eog_hardware_allowed",
    "eog_refuse_authority_conversion",
    "eog_refuse_stale_approval",
    "eog_static_fixtures_only",
]
