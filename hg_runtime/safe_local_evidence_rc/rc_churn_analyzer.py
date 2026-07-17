"""SLE-RC-X churn analyzer.

Determines, deterministically, whether the extended soak produced any
*unexpected* drift. Expected noise — timestamps, proof-bundle paths, and other
per-run fields enumerated in ``STABLE_HASH_EXCLUDE`` — is excluded from the
stable hash by construction. Any difference in stable hashes across iterations is
therefore unexpected churn.

This is a determinism analysis over the soak iteration hashes, not a git-status
scan, so it never races the gate writing its own proof bundle.
"""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.schemas import (
    STABLE_HASH_EXCLUDE,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def analyze_churn(*, iteration_hashes: list[str], boundary_matrix_hashes: list[str], regression_matrix_hash: str) -> dict:
    distinct_iteration_hashes = sorted(set(iteration_hashes))
    distinct_boundary_hashes = sorted(set(boundary_matrix_hashes))
    iteration_drift = len(distinct_iteration_hashes) > 1
    boundary_drift = len(distinct_boundary_hashes) > 1
    record = {
        "schema_version": "1",
        "record_type": "rc_churn_analysis_v1",
        "iteration_count": len(iteration_hashes),
        "distinct_iteration_hash_count": len(distinct_iteration_hashes),
        "distinct_boundary_matrix_hash_count": len(distinct_boundary_hashes),
        "regression_matrix_hash": regression_matrix_hash,
        "iteration_hash_drift_detected": iteration_drift,
        "boundary_matrix_drift_detected": boundary_drift,
        "unexpected_churn_detected": iteration_drift or boundary_drift,
        "excluded_noise_fields": sorted(STABLE_HASH_EXCLUDE),
        "doctrine_note": "Excluded noise (timestamps/proof paths) is not churn; stable-hash drift is.",
        "soak_treated_as_truth": False,
        "stable_hash_treated_as_correctness": False,
        **neutral_flags(),
    }
    record["analysis_hash"] = record_hash(record)
    assert_neutral(record)
    return record
