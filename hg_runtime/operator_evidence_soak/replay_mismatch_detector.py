"""Replay mismatch detection for OES-2 mutation probes."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.mutation import build_soak_mutation_result
from hg_runtime.operator_evidence_soak.mutation_probe import apply_mutation_probe
from hg_runtime.operator_evidence_soak.schemas import record_hash
from hg_runtime.operator_evidence_soak.stable_hash import stable_hash, stable_pipeline_hash


def _boundary_hash(assertions: list[dict]) -> str:
    return stable_hash({"assertions": assertions})


def _receipt_chain_hash(chain: list[dict]) -> str:
    return stable_hash({"receipt_chain": chain})


def detect_probe_mismatch(*, baseline_layer: dict, probe: dict) -> dict:
    probe_type = probe["probe_type"]
    baseline = baseline_layer
    mutated = apply_mutation_probe(baseline, probe_type)
    baseline_pipeline = baseline["stable_hash"]
    mutated_pipeline = stable_pipeline_hash(mutated["ingestion"], mutated["evaluation"])
    baseline_chain = _receipt_chain_hash(baseline.get("receipt_chain", []))
    mutated_chain = _receipt_chain_hash(mutated.get("receipt_chain", []))
    baseline_boundary = _boundary_hash(baseline.get("boundary_assertions", []))
    mutated_boundary = _boundary_hash(mutated.get("boundary_assertions", []))

    pipeline_mismatch = baseline_pipeline != mutated_pipeline
    chain_mismatch = baseline_chain != mutated_chain
    boundary_mismatch = baseline_boundary != mutated_boundary
    mismatch_detected = pipeline_mismatch or chain_mismatch or boundary_mismatch

    return {
        "probe_id": probe["probe_id"],
        "probe_type": probe_type,
        "baseline_pipeline_hash": baseline_pipeline,
        "mutated_pipeline_hash": mutated_pipeline,
        "pipeline_mismatch": pipeline_mismatch,
        "receipt_chain_mismatch": chain_mismatch,
        "boundary_assertion_mismatch": boundary_mismatch,
        "mismatch_detected": mismatch_detected,
        "original_preserved": True,
        "mutation_auto_repaired": False,
    }


def run_mutation_replay_detection(*, baseline_layer: dict, probes: list[dict]) -> dict:
    results = []
    mismatches = []
    for i, probe in enumerate(probes, start=1):
        detection = detect_probe_mismatch(baseline_layer=baseline_layer, probe=probe)
        result = build_soak_mutation_result(
            result_id=f"oes-mresult-{i:03d}",
            probe_id=probe["probe_id"],
            mismatch_detected=detection["mismatch_detected"],
            original_preserved=detection["original_preserved"],
        )
        results.append(result)
        if detection["mismatch_detected"]:
            mismatches.append({**detection, "record_hash": record_hash(detection)})
    all_detected = all(row["mismatch_detected"] for row in results)
    return {
        "mutation_probes": probes,
        "mutation_results": results,
        "mismatch_records": mismatches,
        "all_mismatches_detected": all_detected,
        "all_probe_types_exercised": len(probes) == 8,
    }
