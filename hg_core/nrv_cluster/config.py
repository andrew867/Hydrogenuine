"""NRV cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def nrv_enabled() -> bool:
    return _flag("HG_NRV_ENABLED", default="0")


def nrv_static_fixtures_only() -> bool:
    return _flag("HG_NRV_STATIC_FIXTURES_ONLY", default="1")


def nrv_refuse_authority_conversion() -> bool:
    return _flag("HG_NRV_REFUSE_AUTHORITY_CONVERSION", default="1")


def nrv_refuse_live_model_invocation() -> bool:
    return _flag("HG_NRV_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "nrv_enabled",
    "nrv_refuse_authority_conversion",
    "nrv_refuse_live_model_invocation",
    "nrv_static_fixtures_only",
]
