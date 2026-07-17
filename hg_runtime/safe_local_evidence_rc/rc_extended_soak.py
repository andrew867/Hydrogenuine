"""SLE-RC-X extended regression soak orchestrator.

Runs a longer, deterministic SLE-RC regression soak with NO new feature or
ingestion surface. It reuses the existing RC soak runner (OEC corpus path + DTX
safe-text document path + DTX mutation summary), replays the boundary matrix once
per iteration, cross-checks the OEC/DTX/OES regression paths, and analyzes churn.

Soak is not proof of correctness. Replay match is not truth. Stable hash is not
correctness. Mutation detection is not repair.
"""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.boundary_matrix import build_boundary_matrix
from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result
from hg_runtime.safe_local_evidence_rc.rc_churn_analyzer import analyze_churn
from hg_runtime.safe_local_evidence_rc.rc_regression_matrix import build_regression_matrix
from hg_runtime.safe_local_evidence_rc.rc_soak_runner import run_rc_soak
from hg_runtime.safe_local_evidence_rc.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    assert_neutral,
    neutral_flags,
    record_hash,
)

EXTENDED_SOAK_ITERATION_COUNT = 10


def _boundary_matrix_replays(root: Path, *, upstream_green: bool, iteration_count: int) -> list[dict]:
    replays = []
    for i in range(1, iteration_count + 1):
        matrix = build_boundary_matrix(root, upstream_green=upstream_green)["rc_boundary_matrix"]
        replays.append(
            {
                "schema_version": "1",
                "record_type": "rc_boundary_matrix_replay_v1",
                "iteration_number": i,
                "matrix_hash": matrix["matrix_hash"],
                "failure_count": matrix["failure_count"],
                "phase19_yellow_preserved": matrix["phase19_yellow_preserved"],
                "phase24_infrastructure_only_preserved": matrix["phase24_infrastructure_only_preserved"],
                **neutral_flags(),
            }
        )
    return replays


def run_extended_soak(root: Path, *, iteration_count: int = EXTENDED_SOAK_ITERATION_COUNT) -> dict:
    soak = run_rc_soak(root, iteration_count=iteration_count)
    regression = build_regression_matrix(root)
    upstream_green = regression["all_paths_green"]
    boundary_replays = _boundary_matrix_replays(root, upstream_green=upstream_green, iteration_count=iteration_count)

    iteration_hashes = [row["stable_hash"] for row in soak["rc_soak_iterations"]]
    boundary_hashes = [row["matrix_hash"] for row in boundary_replays]
    churn = analyze_churn(
        iteration_hashes=iteration_hashes,
        boundary_matrix_hashes=boundary_hashes,
        regression_matrix_hash=regression["matrix_hash"],
    )

    rc_consolidation_verdict, rc_consolidation_proof, _ = latest_gate_result(
        root, "SLE-SAFE-LOCAL-EVIDENCE-RELEASE-CANDIDATE"
    )

    all_iterations_match = soak["rc_replay_result"]["all_iterations_match"]
    boundary_stable = churn["distinct_boundary_matrix_hash_count"] == 1
    iterations_stable = churn["distinct_iteration_hash_count"] == 1

    extended_replay_result = {
        "schema_version": "1",
        "record_type": "rc_extended_replay_result_v1",
        "iteration_count": iteration_count,
        "minimum_iterations_met": iteration_count >= EXTENDED_SOAK_ITERATION_COUNT,
        "all_iterations_match": all_iterations_match,
        "iterations_stable": iterations_stable,
        "boundary_matrix_stable": boundary_stable,
        "regression_all_paths_green": regression["all_paths_green"],
        "unexpected_churn_detected": churn["unexpected_churn_detected"],
        "rc_consolidation_verdict": rc_consolidation_verdict,
        "rc_consolidation_proof": rc_consolidation_proof,
        "mutation_mismatch_detected": soak["rc_mutation_summary"]["mutation_mismatch_detected"],
        "mutation_auto_repaired": False,
        "soak_treated_as_truth": False,
        "replay_match_treated_as_truth": False,
        **neutral_flags(),
    }
    assert_neutral(extended_replay_result)

    stable_hashes = {
        "schema_version": "1",
        "record_type": "rc_extended_stable_hashes_v1",
        "expected_hash": soak["rc_stable_hashes"]["expected_hash"],
        "iteration_hashes": iteration_hashes,
        "boundary_matrix_hashes": boundary_hashes,
        "regression_matrix_hash": regression["matrix_hash"],
        "all_iteration_hashes_equal": iterations_stable,
        "all_boundary_hashes_equal": boundary_stable,
    }
    stable_hashes["stable_hash_record_hash"] = record_hash(stable_hashes)

    manifest = {
        "schema_version": "1",
        "record_type": "rc_extended_soak_manifest_v1",
        "manifest_id": "sle-rc-extended-soak-manifest-v1",
        "iteration_count": iteration_count,
        "minimum_iterations": EXTENDED_SOAK_ITERATION_COUNT,
        "oec_corpus_path_included": regression["oec_corpus_path_included"],
        "dtx_safe_text_path_included": regression["dtx_safe_text_path_included"],
        "oes_mutation_summary_path_included": regression["oes_mutation_summary_path_included"],
        "boundary_matrix_replay_count": len(boundary_replays),
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "no_new_ingestion_capability": True,
        "pdf_ingestion_enabled": False,
        "ocr_ingestion_enabled": False,
        "html_parsing_enabled": False,
        "arbitrary_file_ingestion_enabled": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)

    return {
        "rc_extended_soak_manifest": manifest,
        "rc_extended_soak_iterations": soak["rc_soak_iterations"],
        "rc_extended_stable_hashes": stable_hashes,
        "rc_churn_analysis": churn,
        "rc_boundary_matrix_replays": boundary_replays,
        "rc_extended_replay_result": extended_replay_result,
        "rc_regression_matrix": regression,
        "rc_mutation_summary": soak["rc_mutation_summary"],
    }
