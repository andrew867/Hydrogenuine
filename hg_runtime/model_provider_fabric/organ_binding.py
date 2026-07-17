"""Organ ↔ provider role bindings."""

from __future__ import annotations

from hg_runtime.model_provider_fabric.types import ModelProviderRole, OrganModelBinding

DEFAULT_ORGAN_BINDINGS: tuple[OrganModelBinding, ...] = (
    OrganModelBinding("organ:Agent0", "AGENT0_WAKE", notes="Agent #0 wake/liveness"),
    OrganModelBinding("organ:AIS", "ORGAN_BACKGROUND", notes="Autonomic inference substrate"),
    OrganModelBinding("organ:IMS", "ORGAN_BACKGROUND", ("ORGAN_HEAVY_REASONING",), notes="Inference model scheduler"),
    OrganModelBinding("organ:MBS", "ORGAN_BACKGROUND", notes="Multi-bus substrate"),
    OrganModelBinding("organ:OEF", "CRITIQUE", notes="Organ edge filter"),
    OrganModelBinding("organ:NRV", "SUMMARY", ("ROUTING_ADVISORY",), notes="Nervous routing layer"),
    OrganModelBinding("organ:HRT", "ORGAN_BACKGROUND", notes="Heartbeat/liveness transport"),
    OrganModelBinding("organ:RSP", "ORGAN_BACKGROUND", notes="Token budget / streaming accounting"),
    OrganModelBinding("organ:CIR", "ORGAN_BACKGROUND", notes="Circulatory resource observation"),
    OrganModelBinding("organ:DBB", "STORAGE_RETRIEVAL_SUMMARY", notes="Data/blob bus summaries"),
    OrganModelBinding("organ:ISB", "ORGAN_BACKGROUND", notes="Intuition/salience advisory"),
    OrganModelBinding("organ:OCF", "CRITIQUE", notes="Organ control fields safety observation"),
    OrganModelBinding("organ:OIR", "CRITIQUE", notes="Organ interaction renormalization"),
    OrganModelBinding("organ:MBR", "CRITIQUE", notes="Many-body renormalization safety"),
    OrganModelBinding("organ:AuthorityExplanation", "AUTHORITY_ADVISORY", notes="Authority rationale only — not authority"),
)


def binding_for_organ(organ_id: str) -> OrganModelBinding | None:
    for binding in DEFAULT_ORGAN_BINDINGS:
        if binding.organ_id == organ_id:
            return binding
    return None


def all_bindings() -> tuple[OrganModelBinding, ...]:
    return DEFAULT_ORGAN_BINDINGS


__all__ = ["DEFAULT_ORGAN_BINDINGS", "all_bindings", "binding_for_organ"]
