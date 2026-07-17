"""Replay validation for WMBR-01A matrices.

Replay recomputes the stored hashes of the perspective and divergence matrices
(and the cells/records inside them) and confirms they are unchanged. Any
mutation is rejected. Replay asserts no boundary flag has flipped true.
"""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import REPLAY_RECORD_SCHEMA, assert_neutral, neutral_flags
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _recompute(obj: dict, hash_key: str) -> tuple[str, str]:
    """Return (stored_hash, recomputed_hash) for a hashed artifact."""
    copy = dict(obj)
    stored = copy.pop(hash_key, None)
    recomputed = canonical_hash(copy)
    return stored, recomputed


def replay_matrices(perspective_matrix: dict, divergence_matrix: dict) -> dict:
    failures: list[str] = []

    for cell in perspective_matrix.get("cells", []):
        stored, recomputed = _recompute(cell, "cell_hash")
        if stored != recomputed:
            failures.append(f"cell_hash_mismatch:{cell.get('receipt_id')}")

    pm_stored, pm_recomputed = _recompute(perspective_matrix, "matrix_hash")
    if pm_stored != pm_recomputed:
        failures.append("perspective_matrix_hash_mismatch")

    for record in divergence_matrix.get("records", []):
        stored, recomputed = _recompute(record, "record_hash")
        if stored != recomputed:
            failures.append(f"divergence_record_hash_mismatch:{record.get('prompt_id')}:{record.get('divergence_type')}")

    dm_stored, dm_recomputed = _recompute(divergence_matrix, "matrix_hash")
    if dm_stored != dm_recomputed:
        failures.append("divergence_matrix_hash_mismatch")

    try:
        assert_neutral(perspective_matrix)
        assert_neutral(divergence_matrix)
    except Exception as exc:  # noqa: BLE001 - boundary violation surfaced as failure
        failures.append(f"boundary_violation:{exc}")

    record = {
        "schema": REPLAY_RECORD_SCHEMA,
        "ok": not failures,
        "replay_preserves_matrix_hashes": not failures,
        "failures": failures,
        "perspective_matrix_hash": pm_stored,
        "divergence_matrix_hash": dm_stored,
        **neutral_flags(),
    }
    record["replay_hash"] = canonical_hash({"pm": pm_stored, "dm": dm_stored, "failures": failures})
    return record
