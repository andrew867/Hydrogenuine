"""WDB cluster feature flags — static/fixture scope only."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def wdb_enabled() -> bool:
    return _flag("HG_WDB_ENABLED", default="0")


def wdb_static_fixtures_only() -> bool:
    return _flag("HG_WDB_STATIC_FIXTURES_ONLY", default="1")


def wdb_refuse_authority_conversion() -> bool:
    return _flag("HG_WDB_REFUSE_AUTHORITY_CONVERSION", default="1")


def wdb_refuse_live_model_invocation() -> bool:
    return _flag("HG_WDB_REFUSE_LIVE_MODEL_INVOCATION", default="1")


__all__ = [
    "wdb_enabled",
    "wdb_refuse_authority_conversion",
    "wdb_refuse_live_model_invocation",
    "wdb_static_fixtures_only",
]

