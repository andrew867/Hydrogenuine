"""P29-3 tool workbench mutation probes."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.tool_mediated_workbench.hashing import stable_hash, with_hash
from hg_runtime.tool_mediated_workbench.tool_workbench_soak import stable_run_material
from hg_runtime.tool_mediated_workbench.workbench_dry_run import build_dry_run_layer


def _result(probe_id: str, baseline: str, mutated: str) -> dict:
    record = {
        "record_type": "tool_workbench_mutation_result_v1",
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


def run_tool_workbench_mutation_probes(repo_root: Path) -> dict:
    baseline = stable_hash(stable_run_material(repo_root))
    layer = build_dry_run_layer(repo_root)

    # Probe 1: mutate a tool plan
    mutated_plan_material = stable_run_material(repo_root)
    if mutated_plan_material["plan_hashes"]:
        mutated_plan_material["plan_hashes"][0] = "sha256:mutated_plan_hash"

    # Probe 2: mutate a sandbox result
    mutated_sandbox_material = stable_run_material(repo_root)
    if mutated_sandbox_material["sandbox_hashes"]:
        mutated_sandbox_material["sandbox_hashes"][0] = "sha256:mutated_sandbox_hash"

    # Probe 3: simulate refusal bypass (remove a refusal)
    mutated_refusal_material = stable_run_material(repo_root)
    if mutated_refusal_material["refusal_hashes"]:
        mutated_refusal_material["refusal_hashes"] = mutated_refusal_material["refusal_hashes"][1:]

    probes = [
        {"record_type": "tool_workbench_mutation_probe_v1", "schema_version": "1",
         "probe_id": "mutated_tool_plan", "target": "tool_plan"},
        {"record_type": "tool_workbench_mutation_probe_v1", "schema_version": "1",
         "probe_id": "mutated_sandbox_result", "target": "sandbox_result"},
        {"record_type": "tool_workbench_mutation_probe_v1", "schema_version": "1",
         "probe_id": "refusal_bypass_attempt", "target": "refusal_record"},
    ]
    for probe in probes:
        with_hash(probe, "record_hash")

    results = [
        _result("mutated_tool_plan", baseline, stable_hash(mutated_plan_material)),
        _result("mutated_sandbox_result", baseline, stable_hash(mutated_sandbox_material)),
        _result("refusal_bypass_attempt", baseline, stable_hash(mutated_refusal_material)),
    ]
    return {"baseline_hash": baseline, "probes": probes, "results": results}
