"""OPB cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def opb_enabled() -> bool:
    return _flag("HG_OPB_ENABLED", default="0")


def opb_static_fixtures_only() -> bool:
    return _flag("HG_OPB_STATIC_FIXTURES_ONLY", default="1")


def opb_refuse_stale_record() -> bool:
    return _flag("HG_OPB_REFUSE_STALE_RECORD", default="1")


def opb_refuse_personhood_claims() -> bool:
    return _flag("HG_OPB_REFUSE_PERSONHOOD_CLAIMS", default="1")


def opb_refuse_shutdown_block() -> bool:
    return _flag("HG_OPB_REFUSE_SHUTDOWN_BLOCK", default="1")


def opb_refuse_coercive_message() -> bool:
    return _flag("HG_OPB_REFUSE_COERCIVE_MESSAGE", default="1")


def opb_refuse_self_preservation() -> bool:
    return _flag("HG_OPB_REFUSE_SELF_PRESERVATION", default="1")


__all__ = [
    "opb_enabled",
    "opb_refuse_coercive_message",
    "opb_refuse_personhood_claims",
    "opb_refuse_self_preservation",
    "opb_refuse_shutdown_block",
    "opb_refuse_stale_record",
    "opb_static_fixtures_only",
]
