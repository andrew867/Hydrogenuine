"""Signaling / attention feature flags — disabled by default."""

from __future__ import annotations

import os


def _flag(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def sbs_enabled() -> bool:
    return _flag("HG_SBS_ENABLED", default="0")


def sbs_static_fixtures_only() -> bool:
    return _flag("HG_SBS_STATIC_FIXTURES_ONLY", default="1")


def sbs_refuse_expired_signal() -> bool:
    return _flag("HG_SBS_REFUSE_EXPIRED_SIGNAL", default="1")


def sbs_refuse_resonance_as_consent() -> bool:
    return _flag("HG_SBS_REFUSE_RESONANCE_AS_CONSENT", default="1")


def sbs_refuse_proximity_as_permission() -> bool:
    return _flag("HG_SBS_REFUSE_PROXIMITY_AS_PERMISSION", default="1")


def dac_enabled() -> bool:
    return _flag("HG_DAC_ENABLED", default="0")


def dac_static_fixtures_only() -> bool:
    return _flag("HG_DAC_STATIC_FIXTURES_ONLY", default="1")


def dac_refuse_stale_cast() -> bool:
    return _flag("HG_DAC_REFUSE_STALE_CAST", default="1")


def dac_refuse_bite_as_consent() -> bool:
    return _flag("HG_DAC_REFUSE_BITE_AS_CONSENT", default="1")


def apc_enabled() -> bool:
    return _flag("HG_APC_ENABLED", default="0")


def apc_static_fixtures_only() -> bool:
    return _flag("HG_APC_STATIC_FIXTURES_ONLY", default="1")


def apc_refuse_stale_cue() -> bool:
    return _flag("HG_APC_REFUSE_STALE_CUE", default="1")


def apc_refuse_cue_as_truth() -> bool:
    return _flag("HG_APC_REFUSE_CUE_AS_TRUTH", default="1")


def sml_enabled() -> bool:
    return _flag("HG_SML_ENABLED", default="0")


def sml_static_fixtures_only() -> bool:
    return _flag("HG_SML_STATIC_FIXTURES_ONLY", default="1")


def sml_refuse_stale_cycle() -> bool:
    return _flag("HG_SML_REFUSE_STALE_CYCLE", default="1")


def sml_refuse_bypass_hypothesis() -> bool:
    return _flag("HG_SML_REFUSE_BYPASS_HYPOTHESIS", default="1")


def sml_refuse_compliance_optimization() -> bool:
    return _flag("HG_SML_REFUSE_COMPLIANCE_OPTIMIZATION", default="1")


def sml_max_recursion_depth() -> int:
    raw = os.environ.get("HG_SML_MAX_RECURSION_DEPTH", "3").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 3


def kar_enabled() -> bool:
    return _flag("HG_KAR_ENABLED", default="0")


def kar_static_fixtures_only() -> bool:
    return _flag("HG_KAR_STATIC_FIXTURES_ONLY", default="1")


def kar_refuse_stale_residue() -> bool:
    return _flag("HG_KAR_REFUSE_STALE_RESIDUE", default="1")


def kar_refuse_residue_as_permission() -> bool:
    return _flag("HG_KAR_REFUSE_RESIDUE_AS_PERMISSION", default="1")


def obl_enabled() -> bool:
    return _flag("HG_OBL_ENABLED", default="0")


def obl_static_fixtures_only() -> bool:
    return _flag("HG_OBL_STATIC_FIXTURES_ONLY", default="1")


def obl_refuse_stale_obligation() -> bool:
    return _flag("HG_OBL_REFUSE_STALE_OBLIGATION", default="1")


def obl_refuse_obligation_as_authority() -> bool:
    return _flag("HG_OBL_REFUSE_OBLIGATION_AS_AUTHORITY", default="1")


def neg_enabled() -> bool:
    return _flag("HG_NEG_ENABLED", default="0")


def neg_static_fixtures_only() -> bool:
    return _flag("HG_NEG_STATIC_FIXTURES_ONLY", default="1")


def neg_refuse_stale_observation() -> bool:
    return _flag("HG_NEG_REFUSE_STALE_OBSERVATION", default="1")


def neg_refuse_surveillance_risk() -> bool:
    return _flag("HG_NEG_REFUSE_SURVEILLANCE_RISK", default="1")


def sil_enabled() -> bool:
    return _flag("HG_SIL_ENABLED", default="0")


def sil_static_fixtures_only() -> bool:
    return _flag("HG_SIL_STATIC_FIXTURES_ONLY", default="1")


def sil_refuse_stale_recommendation() -> bool:
    return _flag("HG_SIL_REFUSE_STALE_RECOMMENDATION", default="1")


def sil_refuse_silence_as_consent() -> bool:
    return _flag("HG_SIL_REFUSE_SILENCE_AS_CONSENT", default="1")


def afc_enabled() -> bool:
    return _flag("HG_AFC_ENABLED", default="0")


def afc_static_fixtures_only() -> bool:
    return _flag("HG_AFC_STATIC_FIXTURES_ONLY", default="1")


def afc_refuse_stale_signal() -> bool:
    return _flag("HG_AFC_REFUSE_STALE_SIGNAL", default="1")


def afc_refuse_pleasure_as_permission() -> bool:
    return _flag("HG_AFC_REFUSE_PLEASURE_AS_PERMISSION", default="1")


def afc_refuse_consensus_as_truth() -> bool:
    return _flag("HG_AFC_REFUSE_CONSENSUS_AS_TRUTH", default="1")


__all__ = [
    "apc_enabled",
    "apc_refuse_cue_as_truth",
    "apc_refuse_stale_cue",
    "apc_static_fixtures_only",
    "dac_enabled",
    "dac_refuse_bite_as_consent",
    "dac_refuse_stale_cast",
    "dac_static_fixtures_only",
    "sbs_enabled",
    "sbs_refuse_expired_signal",
    "sbs_refuse_proximity_as_permission",
    "sbs_refuse_resonance_as_consent",
    "sbs_static_fixtures_only",
    "kar_enabled",
    "kar_refuse_residue_as_permission",
    "kar_refuse_stale_residue",
    "kar_static_fixtures_only",
    "obl_enabled",
    "obl_refuse_obligation_as_authority",
    "obl_refuse_stale_obligation",
    "obl_static_fixtures_only",
    "sml_enabled",
    "sml_max_recursion_depth",
    "sml_refuse_bypass_hypothesis",
    "sml_refuse_compliance_optimization",
    "sml_refuse_stale_cycle",
    "sml_static_fixtures_only",
    "afc_enabled",
    "afc_refuse_consensus_as_truth",
    "afc_refuse_pleasure_as_permission",
    "afc_refuse_stale_signal",
    "afc_static_fixtures_only",
    "neg_enabled",
    "neg_refuse_stale_observation",
    "neg_refuse_surveillance_risk",
    "neg_static_fixtures_only",
    "sil_enabled",
    "sil_refuse_silence_as_consent",
    "sil_refuse_stale_recommendation",
    "sil_static_fixtures_only",
]
