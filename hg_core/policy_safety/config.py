"""Policy safety feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def syn_enabled() -> bool:
    return _flag("HG_SYN_ENABLED", default="0")


def syn_block_undisclosed_export() -> bool:
    return _flag("HG_SYN_BLOCK_UNDISCLOSED_EXPORT", default="1")


def aid_enabled() -> bool:
    return _flag("HG_AID_ENABLED", default="0")


def aid_require_evidence_for_capability() -> bool:
    return _flag("HG_AID_REQUIRE_EVIDENCE_FOR_CAPABILITY_CLAIMS", default="1")


def dmi_enabled() -> bool:
    return _flag("HG_DMI_ENABLED", default="0")


def dmi_election_always_review() -> bool:
    return _flag("HG_DMI_ELECTION_ALWAYS_REVIEW", default="1")


def fce_enabled() -> bool:
    return _flag("HG_FCE_ENABLED", default="0")


def fce_fail_closed() -> bool:
    return _flag("HG_FCE_FAIL_CLOSED", default="1")


def vsp_enabled() -> bool:
    return _flag("HG_VSP_ENABLED", default="0")


def vsp_minor_strict_mode() -> bool:
    return _flag("HG_VSP_MINOR_STRICT_MODE", default="1")


def cdo_enabled() -> bool:
    return _flag("HG_CDO_ENABLED", default="0")


def cdo_unknown_to_safe_mode() -> bool:
    return _flag("HG_CDO_UNKNOWN_TO_SAFE_MODE", default="1")


def crt_enabled() -> bool:
    return _flag("HG_CRT_ENABLED", default="0")


def crt_include_exceptions() -> bool:
    return _flag("HG_CRT_INCLUDE_EXCEPTIONS", default="1")


__all__ = [
    "aid_enabled",
    "aid_require_evidence_for_capability",
    "cdo_enabled",
    "cdo_unknown_to_safe_mode",
    "crt_enabled",
    "crt_include_exceptions",
    "dmi_election_always_review",
    "dmi_enabled",
    "fce_enabled",
    "fce_fail_closed",
    "syn_block_undisclosed_export",
    "syn_enabled",
    "vsp_enabled",
    "vsp_minor_strict_mode",
]
