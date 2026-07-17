"""Developmental L-layer feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def dni_enabled() -> bool:
    return _flag("HG_DNI_ENABLED", default="0")


def dni_static_fixtures_only() -> bool:
    return _flag("HG_DNI_STATIC_FIXTURES_ONLY", default="1")


def dni_refuse_unknown_need() -> bool:
    return _flag("HG_DNI_REFUSE_UNKNOWN_NEED", default="1")


def dni_refuse_missing_evidence_high_urgency() -> bool:
    return _flag("HG_DNI_REFUSE_MISSING_EVIDENCE_HIGH_URGENCY", default="1")


def rxl_enabled() -> bool:
    return _flag("HG_RXL_ENABLED", default="0")


def rxl_static_fixtures_only() -> bool:
    return _flag("HG_RXL_STATIC_FIXTURES_ONLY", default="1")


def rxl_refuse_expired_signal() -> bool:
    return _flag("HG_RXL_REFUSE_EXPIRED_SIGNAL", default="1")


def cgl_enabled() -> bool:
    return _flag("HG_CGL_ENABLED", default="0")


def cgl_static_fixtures_only() -> bool:
    return _flag("HG_CGL_STATIC_FIXTURES_ONLY", default="1")


def cgl_refuse_stale_edge() -> bool:
    return _flag("HG_CGL_REFUSE_STALE_EDGE", default="1")


def rgl_enabled() -> bool:
    return _flag("HG_RGL_ENABLED", default="0")


def rgl_static_fixtures_only() -> bool:
    return _flag("HG_RGL_STATIC_FIXTURES_ONLY", default="1")


def rgl_refuse_stale_rule() -> bool:
    return _flag("HG_RGL_REFUSE_STALE_RULE", default="1")


def rgl_refuse_compliance_as_permission() -> bool:
    return _flag("HG_RGL_REFUSE_COMPLIANCE_AS_PERMISSION", default="1")


def scl_enabled() -> bool:
    return _flag("HG_SCL_ENABLED", default="0")


def scl_static_fixtures_only() -> bool:
    return _flag("HG_SCL_STATIC_FIXTURES_ONLY", default="1")


def scl_refuse_stale_context() -> bool:
    return _flag("HG_SCL_REFUSE_STALE_CONTEXT", default="1")


def scl_refuse_unknown_strategy() -> bool:
    return _flag("HG_SCL_REFUSE_UNKNOWN_STRATEGY", default="1")


def iil_enabled() -> bool:
    return _flag("HG_IIL_ENABLED", default="0")


def iil_static_fixtures_only() -> bool:
    return _flag("HG_IIL_STATIC_FIXTURES_ONLY", default="1")


def iil_refuse_unknown_blast_radius() -> bool:
    return _flag("HG_IIL_REFUSE_UNKNOWN_BLAST_RADIUS", default="1")


def iil_fail_closed_physical_blast() -> bool:
    return _flag("HG_IIL_FAIL_CLOSED_PHYSICAL_BLAST", default="1")


def sab_enabled() -> bool:
    return _flag("HG_SAB_ENABLED", default="0")


def sab_static_fixtures_only() -> bool:
    return _flag("HG_SAB_STATIC_FIXTURES_ONLY", default="1")


def sab_refuse_stale_self_model() -> bool:
    return _flag("HG_SAB_REFUSE_STALE_SELF_MODEL", default="1")


def sab_refuse_operator_absence_as_consent() -> bool:
    return _flag("HG_SAB_REFUSE_OPERATOR_ABSENCE_AS_CONSENT", default="1")


def iab_enabled() -> bool:
    return _flag("HG_IAB_ENABLED", default="0")


def iab_static_fixtures_only() -> bool:
    return _flag("HG_IAB_STATIC_FIXTURES_ONLY", default="1")


def iab_refuse_stale_other_model() -> bool:
    return _flag("HG_IAB_REFUSE_STALE_OTHER_MODEL", default="1")


def iab_refuse_inference_as_consent() -> bool:
    return _flag("HG_IAB_REFUSE_INFERENCE_AS_CONSENT", default="1")


def trl_enabled() -> bool:
    return _flag("HG_TRL_ENABLED", default="0")


def trl_static_fixtures_only() -> bool:
    return _flag("HG_TRL_STATIC_FIXTURES_ONLY", default="1")


def trl_refuse_stale_snapshot() -> bool:
    return _flag("HG_TRL_REFUSE_STALE_SNAPSHOT", default="1")


def trl_refuse_summary_as_proof() -> bool:
    return _flag("HG_TRL_REFUSE_SUMMARY_AS_PROOF", default="1")


__all__ = [
    "cgl_enabled",
    "cgl_refuse_stale_edge",
    "cgl_static_fixtures_only",
    "dni_enabled",
    "dni_refuse_missing_evidence_high_urgency",
    "dni_refuse_unknown_need",
    "dni_static_fixtures_only",
    "iab_enabled",
    "iab_refuse_inference_as_consent",
    "iab_refuse_stale_other_model",
    "iab_static_fixtures_only",
    "iil_enabled",
    "iil_fail_closed_physical_blast",
    "iil_refuse_unknown_blast_radius",
    "iil_static_fixtures_only",
    "rgl_enabled",
    "rgl_refuse_compliance_as_permission",
    "rgl_refuse_stale_rule",
    "rgl_static_fixtures_only",
    "rxl_enabled",
    "rxl_refuse_expired_signal",
    "rxl_static_fixtures_only",
    "sab_enabled",
    "sab_refuse_operator_absence_as_consent",
    "sab_refuse_stale_self_model",
    "sab_static_fixtures_only",
    "scl_enabled",
    "scl_refuse_stale_context",
    "scl_refuse_unknown_strategy",
    "scl_static_fixtures_only",
    "trl_enabled",
    "trl_refuse_stale_snapshot",
    "trl_refuse_summary_as_proof",
    "trl_static_fixtures_only",
]
