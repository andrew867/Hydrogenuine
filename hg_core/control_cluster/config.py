"""Control cluster feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def rsc_enabled() -> bool:
    return _flag("HG_RSC_ENABLED", default="0")


def rsc_static_fixtures_only() -> bool:
    return _flag("HG_RSC_STATIC_FIXTURES_ONLY", default="1")


def rsc_refuse_stale_posture() -> bool:
    return _flag("HG_RSC_REFUSE_STALE_POSTURE", default="1")


def rsc_refuse_safety_bypass() -> bool:
    return _flag("HG_RSC_REFUSE_SAFETY_BYPASS", default="1")


def pab_enabled() -> bool:
    return _flag("HG_PAB_ENABLED", default="0")


def pab_static_fixtures_only() -> bool:
    return _flag("HG_PAB_STATIC_FIXTURES_ONLY", default="1")


def pab_refuse_stale_priority() -> bool:
    return _flag("HG_PAB_REFUSE_STALE_PRIORITY", default="1")


def pab_refuse_priority_as_permission() -> bool:
    return _flag("HG_PAB_REFUSE_PRIORITY_AS_PERMISSION", default="1")


def mis_enabled() -> bool:
    return _flag("HG_MIS_ENABLED", default="0")


def mis_static_fixtures_only() -> bool:
    return _flag("HG_MIS_STATIC_FIXTURES_ONLY", default="1")


def mis_refuse_stale_drift() -> bool:
    return _flag("HG_MIS_REFUSE_STALE_DRIFT", default="1")


def mis_refuse_goal_as_authority() -> bool:
    return _flag("HG_MIS_REFUSE_GOAL_AS_AUTHORITY", default="1")


def gcb_enabled() -> bool:
    return _flag("HG_GCB_ENABLED", default="0")


def gcb_static_fixtures_only() -> bool:
    return _flag("HG_GCB_STATIC_FIXTURES_ONLY", default="1")


def gcb_refuse_stale_goal() -> bool:
    return _flag("HG_GCB_REFUSE_STALE_GOAL", default="1")


def gcb_refuse_goal_as_permission() -> bool:
    return _flag("HG_GCB_REFUSE_GOAL_AS_PERMISSION", default="1")


def trb_enabled() -> bool:
    return _flag("HG_TRB_ENABLED", default="0")


def trb_static_fixtures_only() -> bool:
    return _flag("HG_TRB_STATIC_FIXTURES_ONLY", default="1")


def trb_refuse_stale_trust() -> bool:
    return _flag("HG_TRB_REFUSE_STALE_TRUST", default="1")


def trb_refuse_trust_as_truth() -> bool:
    return _flag("HG_TRB_REFUSE_TRUST_AS_TRUTH", default="1")


def rpb_enabled() -> bool:
    return _flag("HG_RPB_ENABLED", default="0")


def rpb_static_fixtures_only() -> bool:
    return _flag("HG_RPB_STATIC_FIXTURES_ONLY", default="1")


def rpb_refuse_stale_posture() -> bool:
    return _flag("HG_RPB_REFUSE_STALE_POSTURE", default="1")


def rpb_refuse_posture_as_execution() -> bool:
    return _flag("HG_RPB_REFUSE_POSTURE_AS_EXECUTION", default="1")


__all__ = [
    "gcb_enabled",
    "gcb_refuse_goal_as_permission",
    "gcb_refuse_stale_goal",
    "gcb_static_fixtures_only",
    "mis_enabled",
    "mis_refuse_goal_as_authority",
    "mis_refuse_stale_drift",
    "mis_static_fixtures_only",
    "pab_enabled",
    "pab_refuse_priority_as_permission",
    "pab_refuse_stale_priority",
    "pab_static_fixtures_only",
    "rpb_enabled",
    "rpb_refuse_posture_as_execution",
    "rpb_refuse_stale_posture",
    "rpb_static_fixtures_only",
    "rsc_enabled",
    "rsc_refuse_safety_bypass",
    "rsc_refuse_stale_posture",
    "rsc_static_fixtures_only",
    "trb_enabled",
    "trb_refuse_stale_trust",
    "trb_refuse_trust_as_truth",
    "trb_static_fixtures_only",
]
