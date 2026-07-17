"""P27-3 skill graph mutation probes."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.skill_graph.hashing import stable_hash, with_hash
from hg_runtime.skill_graph.skill_graph_soak import stable_run_material
from hg_runtime.skill_graph.transfer_candidate_builder import build_transfer_candidates


def _result(probe_id: str, baseline: str, mutated: str) -> dict:
    record = {
        "record_type": "skill_graph_mutation_result_v1",
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


def run_skill_graph_mutation_probes(repo_root: Path) -> dict:
    baseline = stable_hash(stable_run_material(repo_root))
    layer = build_transfer_candidates(repo_root)
    mutated_skill = build_transfer_candidates(repo_root)
    mutated_skill["skill_records"][0] = {**mutated_skill["skill_records"][0], "procedure_tag": "mutated_procedure"}
    mutated_skill["skill_records"][0]["skill_hash"] = stable_hash(mutated_skill["skill_records"][0])
    mutated_transfer = build_transfer_candidates(repo_root)
    mutated_transfer["transfer_candidates"][0] = {
        **mutated_transfer["transfer_candidates"][0],
        "link_reason": "mutated_transfer_reason",
    }
    mutated_transfer["transfer_candidates"][0]["transfer_hash"] = stable_hash(mutated_transfer["transfer_candidates"][0])
    missing_provenance = build_transfer_candidates(repo_root)
    missing_provenance["skill_records"][0] = {**missing_provenance["skill_records"][0], "provenance_refs": []}
    missing_provenance["skill_records"][0]["skill_hash"] = stable_hash(missing_provenance["skill_records"][0])
    probes = [
        {"record_type": "skill_graph_mutation_probe_v1", "schema_version": "1", "probe_id": "mutated_skill_source", "target": "skill_record"},
        {"record_type": "skill_graph_mutation_probe_v1", "schema_version": "1", "probe_id": "mutated_transfer_candidate", "target": "transfer_candidate"},
        {"record_type": "skill_graph_mutation_probe_v1", "schema_version": "1", "probe_id": "missing_provenance", "target": "provenance_refs"},
    ]
    for probe in probes:
        with_hash(probe, "record_hash")
    results = [
        _result(
            "mutated_skill_source",
            baseline,
            stable_hash({**stable_run_material(repo_root), "skill_hashes": [row["skill_hash"] for row in mutated_skill["skill_records"]]}),
        ),
        _result(
            "mutated_transfer_candidate",
            baseline,
            stable_hash(
                {
                    **stable_run_material(repo_root),
                    "transfer_hashes": [row["transfer_hash"] for row in mutated_transfer["transfer_candidates"]],
                }
            ),
        ),
        _result(
            "missing_provenance",
            baseline,
            stable_hash({**stable_run_material(repo_root), "skill_hashes": [row["skill_hash"] for row in missing_provenance["skill_records"]]}),
        ),
    ]
    return {"baseline_hash": baseline, "probes": probes, "results": results, "layer": layer}
