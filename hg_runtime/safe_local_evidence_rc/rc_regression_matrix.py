"""SLE-RC-X regression matrix across OEC corpus, DTX safe-text, and OES paths.

The regression matrix is a descriptive cross-check of the release-candidate
component paths. It is not truth, not authority, and not deployment permission.
It only records whether each component path's latest consolidation gate is still
GREEN and links its stable references.
"""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result
from hg_runtime.safe_local_evidence_rc.schemas import assert_neutral, neutral_flags, record_hash

# (regression path id, component family, proof root, expected verdict).
REGRESSION_PATHS = (
    ("oec_corpus_path", "OEC", "OEC-OPERATOR-EVIDENCE-CORPUS-CONSOLIDATION", "GREEN_OEC_OPERATOR_EVIDENCE_CORPUS_CONSOLIDATION"),
    ("dtx_safe_text_path", "DTX", "DTX-SAFE-TEXT-DOCUMENT-EXCHANGE-CONSOLIDATION", "GREEN_DTX_SAFE_TEXT_DOCUMENT_EXCHANGE_CONSOLIDATION"),
    ("oes_mutation_summary_path", "OES", "OES-OPERATOR-EVIDENCE-SOAK-CONSOLIDATION", "GREEN_OES_OPERATOR_EVIDENCE_SOAK_CONSOLIDATION"),
)


def build_regression_path_record(*, path_id: str, component_family: str, proof_root: str, gate_verdict: str, proof_bundle: str, expected: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_regression_path_v1",
        "path_id": path_id,
        "component_family": component_family,
        "proof_root": proof_root,
        "gate_verdict": gate_verdict,
        "proof_bundle": proof_bundle,
        "expected_verdict": expected,
        "is_green": gate_verdict == expected and gate_verdict.startswith("GREEN"),
        "soak_treated_as_truth": False,
        "stable_hash_treated_as_correctness": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_regression_matrix(root: Path) -> dict:
    rows = []
    for path_id, family, proof_root, expected in REGRESSION_PATHS:
        verdict, proof, _ = latest_gate_result(root, proof_root)
        rows.append(
            build_regression_path_record(
                path_id=path_id,
                component_family=family,
                proof_root=proof_root,
                gate_verdict=verdict,
                proof_bundle=proof,
                expected=expected,
            )
        )
    matrix = {
        "schema_version": "1",
        "record_type": "rc_regression_matrix_v1",
        "path_count": len(rows),
        "green_path_count": sum(1 for row in rows if row["is_green"]),
        "all_paths_green": all(row["is_green"] for row in rows),
        "oec_corpus_path_included": any(row["path_id"] == "oec_corpus_path" for row in rows),
        "dtx_safe_text_path_included": any(row["path_id"] == "dtx_safe_text_path" for row in rows),
        "oes_mutation_summary_path_included": any(row["path_id"] == "oes_mutation_summary_path" for row in rows),
        "paths": rows,
        **neutral_flags(),
    }
    matrix["matrix_hash"] = record_hash(matrix)
    assert_neutral(matrix)
    return matrix
