"""Replay validation for WMBR-06 world-model audit artifacts."""

from __future__ import annotations

from hg_runtime.world_model_audit.schemas import (
    REPLAY_RECORD_SCHEMA,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _recompute(obj: dict, hash_key: str) -> tuple[str | None, str]:
    copy = dict(obj)
    stored = copy.pop(hash_key, None)
    return stored, canonical_hash(copy)


def replay_audit(
    record_audits: list[dict],
    stale_markers: list[dict],
    decay_records: list[dict],
    contradiction_audits: list[dict],
    failed_prediction_audits: list[dict],
    retraction_closures: list[dict],
    maintenance_policy: dict,
    manifest: dict,
) -> dict:
    failures: list[str] = []

    for group_name, group, hash_key in (
        ("record_audit", record_audits, "audit_hash"),
        ("stale_marker", stale_markers, "marker_hash"),
        ("decay_record", decay_records, "decay_hash"),
        ("contradiction_audit", contradiction_audits, "audit_hash"),
        ("failed_prediction_audit", failed_prediction_audits, "audit_hash"),
        ("retraction_closure", retraction_closures, "closure_hash"),
    ):
        for rec in group:
            stored, recomputed = _recompute(rec, hash_key)
            if stored != recomputed:
                failures.append(f"{group_name}_hash_mismatch:{rec.get('audit_id') or rec.get('marker_id') or rec.get('decay_id')}")

    stored_p, recomputed_p = _recompute(maintenance_policy, "policy_hash")
    if stored_p != recomputed_p:
        failures.append("maintenance_policy_hash_mismatch")

    stored_m, recomputed_m = _recompute(manifest, "manifest_hash")
    if stored_m != recomputed_m:
        failures.append("manifest_hash_mismatch")

    try:
        for group in (
            record_audits,
            stale_markers,
            decay_records,
            contradiction_audits,
            failed_prediction_audits,
            retraction_closures,
        ):
            for rec in group:
                assert_neutral(rec)
        assert_neutral(maintenance_policy)
        assert_neutral(manifest)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"boundary_violation:{exc}")

    record = {
        "schema": REPLAY_RECORD_SCHEMA,
        "ok": not failures,
        "replay_preserves_audit_hashes": not failures,
        "failures": failures,
        "manifest_hash": stored_m,
        "record_audit_count": len(record_audits),
        "stale_marker_count": len(stale_markers),
        "decay_record_count": len(decay_records),
        **neutral_flags(),
    }
    record["replay_hash"] = canonical_hash({"manifest_hash": stored_m, "failures": failures})
    return record
