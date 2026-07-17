"""P26-4 mutation probes."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.hashing import stable_hash, with_hash
from hg_runtime.experience_ledger.p26_recall_soak import stable_run_material
from hg_runtime.experience_ledger.promotion_decision_ledger import build_p26_3_bridge
from hg_runtime.experience_ledger.recall_index import build_recall_index


def _result(probe_id: str, baseline: str, mutated: str) -> dict:
    result = {
        "record_type": "p26_mutation_result_v1",
        "schema_version": "1",
        "probe_id": probe_id,
        "baseline_hash": baseline,
        "mutated_hash": mutated,
        "mutation_detected": baseline != mutated,
        "mutation_auto_repair_performed": False,
        "original_artifacts_mutated": False,
    }
    with_hash(result, "record_hash")
    return result


def run_mutation_probes(repo_root: Path) -> dict:
    baseline = stable_hash(stable_run_material(repo_root))
    recall_index = build_recall_index(repo_root)
    mutated_memory = build_recall_index(repo_root)
    mutated_memory["index"]["entries"][0]["memory_hash"] = "sha256:mutated-memory-record"
    mutated_provenance = build_recall_index(repo_root)
    mutated_provenance["index"]["entries"][0]["provenance_refs"] = ["mutated-provenance-pointer"]
    promotion = build_p26_3_bridge(repo_root)
    promotion["decisions"][0]["decision_status"] = "MUTATED_DECISION"
    probes = [
        {"record_type": "p26_mutation_probe_v1", "schema_version": "1", "probe_id": "memory_record_mutation", "target": "memory_record"},
        {"record_type": "p26_mutation_probe_v1", "schema_version": "1", "probe_id": "provenance_pointer_mutation", "target": "provenance_pointer"},
        {"record_type": "p26_mutation_probe_v1", "schema_version": "1", "probe_id": "promotion_decision_mutation", "target": "promotion_decision"},
    ]
    results = [
        _result("memory_record_mutation", baseline, stable_hash({**stable_run_material(repo_root), "recall_index_hash": stable_hash(mutated_memory["index"])})),
        _result("provenance_pointer_mutation", baseline, stable_hash({**stable_run_material(repo_root), "recall_index_hash": stable_hash(mutated_provenance["index"])})),
        _result("promotion_decision_mutation", baseline, stable_hash({**stable_run_material(repo_root), "promotion_decision_hashes": [stable_hash(d) for d in promotion["decisions"]]})),
    ]
    for probe in probes:
        with_hash(probe, "record_hash")
    return {"baseline_hash": baseline, "probes": probes, "results": results, "recall_index": recall_index}
