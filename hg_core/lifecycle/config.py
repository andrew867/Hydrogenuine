"""Lifecycle feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def crr_alignment_enabled() -> bool:
    return _flag("HG_CRR_ALIGNMENT_ENABLED", default="0")


def crr_refuse_stale_alignment() -> bool:
    return _flag("HG_CRR_REFUSE_STALE_ALIGNMENT", default="1")


def crr_static_fixtures_only() -> bool:
    return _flag("HG_CRR_STATIC_FIXTURES_ONLY", default="1")


def crr_forbid_process_kill() -> bool:
    return _flag("HG_CRR_FORBID_PROCESS_KILL", default="1")


def crr_forbid_successor_spawn() -> bool:
    return _flag("HG_CRR_FORBID_SUCCESSOR_SPAWN", default="1")


def mor_enabled() -> bool:
    return _flag("HG_MOR_ENABLED", default="0")


def mor_static_fixtures_only() -> bool:
    return _flag("HG_MOR_STATIC_FIXTURES_ONLY", default="1")


def mor_forbid_process_kill() -> bool:
    return _flag("HG_MOR_FORBID_PROCESS_KILL", default="1")


def mor_forbid_successor_spawn() -> bool:
    return _flag("HG_MOR_FORBID_SUCCESSOR_SPAWN", default="1")


def mor_refuse_stale_death_notice() -> bool:
    return _flag("HG_MOR_REFUSE_STALE_DEATH_NOTICE", default="1")


def cnt_enabled() -> bool:
    return _flag("HG_CNT_ENABLED", default="0")


def cnt_static_fixtures_only() -> bool:
    return _flag("HG_CNT_STATIC_FIXTURES_ONLY", default="1")


def cnt_refuse_identity_continuity() -> bool:
    return _flag("HG_CNT_REFUSE_IDENTITY_CONTINUITY", default="1")


def cnt_refuse_stale_authority_inheritance() -> bool:
    return _flag("HG_CNT_REFUSE_STALE_AUTHORITY_INHERITANCE", default="1")


__all__ = [
    "cnt_enabled",
    "cnt_refuse_identity_continuity",
    "cnt_refuse_stale_authority_inheritance",
    "cnt_static_fixtures_only",
    "crr_alignment_enabled",
    "crr_forbid_process_kill",
    "crr_forbid_successor_spawn",
    "crr_refuse_stale_alignment",
    "crr_static_fixtures_only",
    "mor_enabled",
    "mor_forbid_process_kill",
    "mor_forbid_successor_spawn",
    "mor_refuse_stale_death_notice",
    "mor_static_fixtures_only",
]
