"""DTX mutation probes for soak mismatch detection."""

from __future__ import annotations

import copy

from hg_runtime.document_text_exchange.schemas import MUTATION_PROBE_TYPES, assert_neutral, neutral_flags, record_hash


def build_mutation_probe(*, probe_id: str, probe_type: str, target_ref: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_mutation_probe_v1",
        "probe_id": probe_id,
        "probe_type": probe_type,
        "target_ref": target_ref,
        "mutation_detection_is_repair": False,
        "mutation_auto_repaired": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_mutation_probes() -> list[dict]:
    return [
        build_mutation_probe(
            probe_id=f"dtx-mprobe-{i:03d}",
            probe_type=probe_type,
            target_ref=f"dtx-target-{probe_type.lower()}",
        )
        for i, probe_type in enumerate(sorted(MUTATION_PROBE_TYPES), start=1)
    ]


def _copy_baseline(baseline: dict) -> dict:
    return {
        "bridge_layer": copy.deepcopy(baseline["bridge_layer"]),
        "evaluation_layer": copy.deepcopy(baseline["evaluation_layer"]),
        "stable_hash": baseline["stable_hash"],
        "dtx_manifest_ref": baseline["dtx_manifest_ref"],
    }


def apply_mutation_probe(baseline: dict, probe_type: str) -> dict:
    if probe_type not in MUTATION_PROBE_TYPES:
        raise ValueError(f"invalid_probe_type:{probe_type}")
    copied = _copy_baseline(baseline)
    bridge = copied["bridge_layer"]
    evaluation = copied["evaluation_layer"]
    if probe_type == "MODIFIED_EXTRACTION_RECEIPT_HASH":
        bridge["dtx_extraction_receipts"][0]["content_hash"] = "mutated-content-hash"
    elif probe_type == "MODIFIED_PACKET_SUPPORT_RECORD":
        evaluation["dtx_claim_packets"][0]["support_record_ids"] = ["mutated-support-id"]
    elif probe_type == "MODIFIED_DASHBOARD_SUMMARY":
        evaluation["dtx_operator_dashboard"]["claim_packet_count"] = 999
    elif probe_type == "MODIFIED_SECOND_SOURCE_RESULT":
        evaluation["dtx_second_source_results"][0]["outcome"] = "MUTATED_OUTCOME"
    elif probe_type == "MODIFIED_CONTRADICTION_PACKET":
        if evaluation["dtx_contradiction_packets"]:
            evaluation["dtx_contradiction_packets"][0]["claim_id"] = "mutated-claim-id"
        else:
            evaluation["dtx_claim_packets"][0]["contradiction_record_ids"] = ["mutated-contradiction"]
    from hg_runtime.document_text_exchange.dtx_stable_hash import stable_pipeline_hash

    copied["stable_hash"] = stable_pipeline_hash(bridge, evaluation)
    return copied


def build_mutation_result(*, result_id: str, probe_id: str, probe_type: str, baseline_hash: str, observed_hash: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_mutation_result_v1",
        "result_id": result_id,
        "probe_id": probe_id,
        "probe_type": probe_type,
        "baseline_hash": baseline_hash,
        "observed_hash": observed_hash,
        "mismatch_detected": baseline_hash != observed_hash,
        "mutation_detection_is_repair": False,
        "mutation_auto_repaired": False,
        "deletion_performed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def run_mutation_detection(*, baseline_layer: dict, probes: list[dict]) -> dict:
    baseline_hash = baseline_layer["stable_hash"]
    results = []
    for idx, probe in enumerate(probes, start=1):
        mutated = apply_mutation_probe(baseline_layer, probe["probe_type"])
        results.append(
            build_mutation_result(
                result_id=f"dtx-mresult-{idx:03d}",
                probe_id=probe["probe_id"],
                probe_type=probe["probe_type"],
                baseline_hash=baseline_hash,
                observed_hash=mutated["stable_hash"],
            )
        )
    return {
        "dtx_mutation_probes": probes,
        "dtx_mutation_results": results,
        "all_mismatches_detected": all(row["mismatch_detected"] for row in results),
    }


def build_mutation_layer(baseline_layer: dict) -> dict:
    probes = build_mutation_probes()
    return {"baseline": baseline_layer, "probes": probes, **run_mutation_detection(baseline_layer=baseline_layer, probes=probes)}
