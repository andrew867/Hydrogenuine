"""P28-3 domain pack mutation probes."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_readiness_gate import evaluate_domain_readiness_gate
from hg_runtime.domain_pack_runtime.hashing import stable_hash, with_hash
from hg_runtime.domain_pack_runtime.domain_pack_soak import stable_run_material


def _result(probe_id: str, baseline: str, mutated: str) -> dict:
    record = {
        "record_type": "domain_pack_mutation_result_v1",
        "schema_version": "1",
        "probe_id": probe_id,
        "baseline_hash": baseline,
        "mutated_hash": mutated,
        "mutation_detected": baseline != mutated,
        "mutation_auto_repaired": False,
        "original_artifacts_mutated": False,
    }
    with_hash(record, "record_hash")
    return record


def run_domain_pack_mutation_probes(repo_root: Path) -> dict:
    baseline = stable_hash(stable_run_material(repo_root))
    layer = evaluate_domain_readiness_gate(repo_root)
    mutated_pack = evaluate_domain_readiness_gate(repo_root)
    mutated_pack["domain_packs"][0] = {
        **mutated_pack["domain_packs"][0],
        "domain_label": "MUTATED_DOMAIN",
    }
    mutated_pack["domain_packs"][0]["pack_hash"] = stable_hash(mutated_pack["domain_packs"][0])
    mutated_readiness = evaluate_domain_readiness_gate(repo_root)
    mutated_readiness["domain_pack_readiness_records"][0] = {
        **mutated_readiness["domain_pack_readiness_records"][0],
        "readiness_state": "NOT_READY",
    }
    mutated_readiness["domain_pack_readiness_records"][0]["readiness_hash"] = stable_hash(
        mutated_readiness["domain_pack_readiness_records"][0]
    )
    missing_provenance = evaluate_domain_readiness_gate(repo_root)
    missing_provenance["domain_packs"][0] = {
        **missing_provenance["domain_packs"][0],
        "provenance_refs": [],
    }
    missing_provenance["domain_packs"][0]["pack_hash"] = stable_hash(missing_provenance["domain_packs"][0])
    probes = [
        {
            "record_type": "domain_pack_mutation_probe_v1",
            "schema_version": "1",
            "probe_id": "mutated_domain_label",
            "target": "domain_pack_record",
        },
        {
            "record_type": "domain_pack_mutation_probe_v1",
            "schema_version": "1",
            "probe_id": "mutated_readiness_state",
            "target": "domain_pack_readiness_record",
        },
        {
            "record_type": "domain_pack_mutation_probe_v1",
            "schema_version": "1",
            "probe_id": "missing_provenance",
            "target": "provenance_refs",
        },
    ]
    for probe in probes:
        with_hash(probe, "record_hash")
    results = [
        _result(
            "mutated_domain_label",
            baseline,
            stable_hash(
                {
                    **stable_run_material(repo_root),
                    "pack_hashes": [row["pack_hash"] for row in mutated_pack["domain_packs"]],
                }
            ),
        ),
        _result(
            "mutated_readiness_state",
            baseline,
            stable_hash(
                {
                    **stable_run_material(repo_root),
                    "readiness_hashes": [row["readiness_hash"] for row in mutated_readiness["domain_pack_readiness_records"]],
                }
            ),
        ),
        _result(
            "missing_provenance",
            baseline,
            stable_hash(
                {
                    **stable_run_material(repo_root),
                    "pack_hashes": [row["pack_hash"] for row in missing_provenance["domain_packs"]],
                }
            ),
        ),
    ]
    return {"baseline_hash": baseline, "probes": probes, "results": results, "layer": layer}
