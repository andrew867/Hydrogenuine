"""Deterministic OES-0 schema foundation fixtures."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.boundary_assertions import build_default_boundary_assertions
from hg_runtime.operator_evidence_soak.mutation import build_soak_mutation_probe, build_soak_mutation_result
from hg_runtime.operator_evidence_soak.schemas import MUTATION_PROBE_TYPES
from hg_runtime.operator_evidence_soak.soak_iteration import build_soak_iteration_result, build_soak_replay_result
from hg_runtime.operator_evidence_soak.soak_policy import build_operator_evidence_soak, build_soak_manifest, build_soak_policy


def build_oes0_fixture_records() -> dict:
    policy = build_soak_policy()
    soak = build_operator_evidence_soak(soak_id="oes0-soak-fixture", manifest_id="oes0-manifest-fixture")
    manifest = build_soak_manifest(
        manifest_id="oes0-manifest-fixture",
        corpus_manifest_ref="docs/proofs/autonomous_agent_zero/OEC-1-CURATED-TEXT-CORPUS",
        iteration_count=5,
    )
    iterations = [
        build_soak_iteration_result(
            iteration_id=f"oes0-iter-{i:03d}",
            iteration_number=i,
            stable_hash="sha256:oes0-fixture-stable",
            replay_match=True,
        )
        for i in range(1, 6)
    ]
    replay = build_soak_replay_result(iteration_count=5, stable_hashes=["sha256:oes0-fixture-stable"] * 5, all_match=True)
    probes = [
        build_soak_mutation_probe(probe_id=f"oes0-probe-{i:03d}", probe_type=ptype, target_ref=f"oes0-target-{i:03d}")
        for i, ptype in enumerate(sorted(MUTATION_PROBE_TYPES), start=1)
    ]
    mutation_results = [
        build_soak_mutation_result(result_id=f"oes0-mresult-{i:03d}", probe_id=probe["probe_id"], mismatch_detected=True)
        for i, probe in enumerate(probes, start=1)
    ]
    return {
        "operator_evidence_soak": soak,
        "soak_policy": policy,
        "soak_manifest": manifest,
        "soak_iterations": iterations,
        "soak_replay_result": replay,
        "soak_boundary_assertions": build_default_boundary_assertions(),
        "soak_mutation_probes": probes,
        "soak_mutation_results": mutation_results,
    }
