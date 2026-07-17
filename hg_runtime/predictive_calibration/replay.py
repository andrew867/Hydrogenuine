"""Replay validation for WMBR-05 predictive calibration artifacts.

Replay recomputes candidate, calibration, uncertainty, drift, and manifest
hashes and confirms they are unchanged. Any mutation is rejected.
"""

from __future__ import annotations

from hg_runtime.predictive_calibration.schemas import (
    REPLAY_RECORD_SCHEMA,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _recompute(obj: dict, hash_key: str) -> tuple[str | None, str]:
    copy = dict(obj)
    stored = copy.pop(hash_key, None)
    return stored, canonical_hash(copy)


def replay_calibration(
    prediction_candidates: list[dict],
    calibration_records: list[dict],
    uncertainty_scores: list[dict],
    drift_records: list[dict],
    manifest: dict,
) -> dict:
    failures: list[str] = []

    for cand in prediction_candidates:
        stored, recomputed = _recompute(cand, "candidate_hash")
        if stored != recomputed:
            failures.append(f"candidate_hash_mismatch:{cand.get('prediction_candidate_id')}")

    for cal in calibration_records:
        stored, recomputed = _recompute(cal, "calibration_hash")
        if stored != recomputed:
            failures.append(f"calibration_hash_mismatch:{cal.get('calibration_id')}")

    for unc in uncertainty_scores:
        stored, recomputed = _recompute(unc, "uncertainty_hash")
        if stored != recomputed:
            failures.append(f"uncertainty_hash_mismatch:{unc.get('uncertainty_id')}")

    for drift in drift_records:
        stored, recomputed = _recompute(drift, "drift_hash")
        if stored != recomputed:
            failures.append(f"drift_hash_mismatch:{drift.get('drift_id')}")

    expected_hashes = [c["candidate_hash"] for c in prediction_candidates]
    if expected_hashes != manifest.get("candidate_hashes", []):
        failures.append("candidate_hash_list_mismatch")

    stored_m, recomputed_m = _recompute(manifest, "manifest_hash")
    if stored_m != recomputed_m:
        failures.append("manifest_hash_mismatch")

    try:
        for group in (prediction_candidates, calibration_records, uncertainty_scores, drift_records):
            for rec in group:
                assert_neutral(rec)
        assert_neutral(manifest)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"boundary_violation:{exc}")

    record = {
        "schema": REPLAY_RECORD_SCHEMA,
        "ok": not failures,
        "replay_preserves_calibration_hashes": not failures,
        "failures": failures,
        "manifest_hash": stored_m,
        "prediction_candidate_count": len(prediction_candidates),
        "calibration_record_count": len(calibration_records),
        **neutral_flags(),
    }
    record["replay_hash"] = canonical_hash({"manifest_hash": stored_m, "failures": failures})
    return record
