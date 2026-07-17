"""SLE-RC mutation summary over DTX baseline layer."""

from __future__ import annotations

from hg_runtime.document_text_exchange.dtx_mutation_probe import apply_mutation_probe, build_mutation_probes
from hg_runtime.document_text_exchange.dtx_stable_hash import stable_pipeline_hash
from hg_runtime.safe_local_evidence_rc.schemas import assert_neutral, neutral_flags, record_hash


def build_rc_mutation_summary(*, baseline_layer: dict, expected_hash: str) -> dict:
    probes = build_mutation_probes()
    results = []
    for probe in probes:
        mutated = apply_mutation_probe(baseline_layer, probe["probe_type"])
        mutated_hash = stable_pipeline_hash(mutated["bridge_layer"], mutated["evaluation_layer"])
        mismatch = mutated_hash != baseline_layer["stable_hash"]
        results.append(
            {
                "probe_id": probe["probe_id"],
                "probe_type": probe["probe_type"],
                "mismatch_detected": mismatch,
                "mutation_auto_repaired": False,
                "mutation_detection_is_repair": False,
            }
        )
    summary = {
        "schema_version": "1",
        "record_type": "rc_mutation_summary_v1",
        "probe_count": len(results),
        "mismatch_count": sum(1 for row in results if row["mismatch_detected"]),
        "mutation_mismatch_detected": all(row["mismatch_detected"] for row in results),
        "mutation_auto_repaired": False,
        "mutation_detection_is_repair": False,
        "probe_results": results,
        "expected_hash": expected_hash,
        **neutral_flags(),
    }
    summary["summary_hash"] = record_hash(summary)
    assert_neutral(summary)
    return summary
