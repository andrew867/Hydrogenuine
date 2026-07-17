"""IMS cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def ims_enabled() -> bool:
    return _flag("HG_IMS_ENABLED", default="0")


def ims_static_fixtures_only() -> bool:
    return _flag("HG_IMS_STATIC_FIXTURES_ONLY", default="1")


def ims_refuse_authority_conversion() -> bool:
    return _flag("HG_IMS_REFUSE_AUTHORITY_CONVERSION", default="1")


def ims_refuse_live_model_invocation() -> bool:
    return _flag("HG_IMS_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "ims_enabled",
    "ims_refuse_authority_conversion",
    "ims_refuse_live_model_invocation",
    "ims_static_fixtures_only",
]
