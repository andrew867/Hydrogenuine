"""Deterministic mutation probes over copied soak artifacts."""

from __future__ import annotations

import copy
from typing import Any

from hg_runtime.operator_evidence_soak.mutation import build_soak_mutation_probe
from hg_runtime.operator_evidence_soak.schemas import MUTATION_PROBE_TYPES


def _copy_layer(layer: dict) -> dict:
    return {
        "ingestion": copy.deepcopy(layer["ingestion"]),
        "evaluation": copy.deepcopy(layer["evaluation"]),
        "boundary_assertions": copy.deepcopy(layer.get("boundary_assertions", [])),
        "receipt_chain": copy.deepcopy(layer.get("receipt_chain", [])),
    }


def _mutate(layer: dict, probe_type: str) -> dict:
    copied = _copy_layer(layer)
    ingestion = copied["ingestion"]
    evaluation = copied["evaluation"]
    if probe_type == "MODIFIED_CORPUS_SOURCE_HASH":
        ingestion["corpus_evidence_receipts"][0]["source_id"] = "mutated-source-id"
    elif probe_type == "MODIFIED_EVIDENCE_RECEIPT_HASH":
        ingestion["corpus_evidence_receipts"][0]["evidence_text_excerpt"] = "mutated-evidence-text"
    elif probe_type == "MODIFIED_PACKET_SUPPORT_RECORD":
        evaluation["corpus_claim_packets"][0]["support_record_ids"] = ["mutated-support-id"]
    elif probe_type == "MODIFIED_SECOND_SOURCE_RESULT":
        evaluation["corpus_second_source_results"][0]["outcome"] = "MUTATED_OUTCOME"
    elif probe_type == "MODIFIED_CONTRADICTION_PACKET":
        if evaluation["corpus_contradiction_packets"]:
            evaluation["corpus_contradiction_packets"][0]["claim_id"] = "mutated-claim-id"
        else:
            evaluation["corpus_claim_packets"][0]["contradiction_record_ids"] = ["mutated-contradiction"]
    elif probe_type == "MODIFIED_DASHBOARD_SUMMARY":
        evaluation["corpus_operator_dashboard"]["claim_packet_count"] = 999
    elif probe_type == "REMOVED_RECEIPT_CHAIN_ENTRY":
        copied["receipt_chain"] = layer.get("receipt_chain", ingestion["corpus_evidence_receipts"])[1:]
    elif probe_type == "ALTERED_BOUNDARY_ASSERTION":
        assertions = copied.get("boundary_assertions") or []
        if assertions:
            assertions[0]["soak_not_truth"] = False
    else:
        raise ValueError(f"unknown_probe_type:{probe_type}")
    return copied


def build_mutation_probes() -> list[dict]:
    return [
        build_soak_mutation_probe(
            probe_id=f"oes-mprobe-{i:03d}",
            probe_type=probe_type,
            target_ref=f"oes-target-{probe_type.lower()}",
        )
        for i, probe_type in enumerate(sorted(MUTATION_PROBE_TYPES), start=1)
    ]


def apply_mutation_probe(layer: dict, probe_type: str) -> dict:
    if probe_type not in MUTATION_PROBE_TYPES:
        raise ValueError(f"invalid_probe_type:{probe_type}")
    return _mutate(layer, probe_type)


def build_mutation_layer(baseline_layer: dict) -> dict:
    boundary_assertions = baseline_layer.get("boundary_assertions")
    if boundary_assertions is None:
        from hg_runtime.operator_evidence_soak.boundary_assertions import build_default_boundary_assertions

        boundary_assertions = build_default_boundary_assertions()
    receipt_chain = baseline_layer.get("receipt_chain")
    if receipt_chain is None:
        receipt_chain = baseline_layer["ingestion"]["corpus_evidence_receipts"] + baseline_layer["ingestion"]["corpus_source_excerpt_receipts"]
    enriched = {
        **baseline_layer,
        "boundary_assertions": boundary_assertions,
        "receipt_chain": receipt_chain,
    }
    probes = build_mutation_probes()
    return {"baseline": enriched, "probes": probes}
