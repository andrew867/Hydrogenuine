"""Runtime context feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def bcp_enabled() -> bool:
    return _flag("HG_BCP_ENABLED", default="0")


def bcp_refuse_stale_packet() -> bool:
    return _flag("HG_BCP_REFUSE_STALE_PACKET", default="1")


def pres_enabled() -> bool:
    return _flag("HG_PRES_ENABLED", default="0")


def pres_require_authority_badge() -> bool:
    return _flag("HG_PRES_REQUIRE_AUTHORITY_BADGE", default="1")


def res_enabled() -> bool:
    return _flag("HG_RES_ENABLED", default="0")


def res_offline_only() -> bool:
    return _flag("HG_RES_OFFLINE_ONLY", default="1")


def sim_enabled() -> bool:
    return _flag("HG_SIM_ENABLED", default="0")


def sim_refuse_stale_scenario() -> bool:
    return _flag("HG_SIM_REFUSE_STALE_SCENARIO", default="1")


def sim_offline_only() -> bool:
    return _flag("HG_SIM_OFFLINE_ONLY", default="1")


def pub_enabled() -> bool:
    return _flag("HG_PUB_ENABLED", default="0")


def pub_require_evidence_for_public() -> bool:
    return _flag("HG_PUB_REQUIRE_EVIDENCE_FOR_PUBLIC", default="1")


def dep_bond_enabled() -> bool:
    return _flag("HG_DEP_BOND_ENABLED", default="0")


def dep_bond_refuse_stale_observation() -> bool:
    return _flag("HG_DEP_BOND_REFUSE_STALE_OBSERVATION", default="1")


def pro_enabled() -> bool:
    return _flag("HG_PRO_ENABLED", default="0")


def pro_backburner_guard() -> bool:
    return _flag("HG_PRO_BACKBURNER", default="1")


def pro_refuse_stale_body_state() -> bool:
    return _flag("HG_PRO_REFUSE_STALE_BODY_STATE", default="1")


def pro_static_fixtures_only() -> bool:
    return _flag("HG_PRO_STATIC_FIXTURES_ONLY", default="1")


def pro_hardware_allowed() -> bool:
    return _flag("HG_PRO_HARDWARE_ALLOWED", default="0")


__all__ = [
    "bcp_enabled",
    "bcp_refuse_stale_packet",
    "dep_bond_enabled",
    "dep_bond_refuse_stale_observation",
    "pres_enabled",
    "pres_require_authority_badge",
    "pro_backburner_guard",
    "pro_enabled",
    "pro_hardware_allowed",
    "pro_refuse_stale_body_state",
    "pro_static_fixtures_only",
    "pub_enabled",
    "pub_require_evidence_for_public",
    "res_enabled",
    "res_offline_only",
    "sim_enabled",
    "sim_offline_only",
    "sim_refuse_stale_scenario",
]
