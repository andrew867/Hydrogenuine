"""P30-3 soak artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json


def write_soak_artifacts(proof_dir: Path, soak: dict, probes: dict) -> None:
    write_json(proof_dir / "soak_result.json", {
        "baseline_composite": soak["baseline_composite"],
        "iteration_count": soak["iteration_count"],
        "iterations": soak["iterations"],
        "all_stable": soak["all_stable"],
    })
    write_json(proof_dir / "mutation_probes.json", probes)
