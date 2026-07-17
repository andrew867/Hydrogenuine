"""Replay validation for the WMBR-03 belief revision ledger.

Replay recomputes revision, belief-state, evidence, and manifest hashes and
confirms they are unchanged. Any mutation is rejected. Replay asserts no
boundary flag flipped true (no truth claimed, no certainty claimed, no claim
marked true/false).
"""

from __future__ import annotations

from hg_runtime.belief_revision_ledger.schemas import (
    REPLAY_RECORD_SCHEMA,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _recompute(obj: dict, hash_key: str) -> tuple[str, str]:
    copy = dict(obj)
    stored = copy.pop(hash_key, None)
    return stored, canonical_hash(copy)


def replay_ledger(revisions: list[dict], belief_states: list[dict], evidence_receipts: list[dict], manifest: dict) -> dict:
    failures: list[str] = []

    for rev in revisions:
        stored, recomputed = _recompute(rev, "revision_hash")
        if stored != recomputed:
            failures.append(f"revision_hash_mismatch:{rev.get('revision_id')}")

    for state in belief_states:
        stored, recomputed = _recompute(state, "state_hash")
        if stored != recomputed:
            failures.append(f"state_hash_mismatch:{state.get('belief_state_id')}")

    for receipt in evidence_receipts:
        stored, recomputed = _recompute(receipt, "receipt_hash")
        if stored != recomputed:
            failures.append(f"evidence_hash_mismatch:{receipt.get('evidence_receipt_id')}")

    expected_revision_hashes = [r["revision_hash"] for r in revisions]
    if expected_revision_hashes != manifest.get("revision_hashes", []):
        failures.append("revision_hash_list_mismatch")

    stored_m, recomputed_m = _recompute(manifest, "manifest_hash")
    if stored_m != recomputed_m:
        failures.append("manifest_hash_mismatch")

    try:
        for rev in revisions:
            assert_neutral(rev)
        for state in belief_states:
            assert_neutral(state)
        for receipt in evidence_receipts:
            assert_neutral(receipt)
        assert_neutral(manifest)
    except Exception as exc:  # noqa: BLE001 - boundary violation surfaced as failure
        failures.append(f"boundary_violation:{exc}")

    record = {
        "schema": REPLAY_RECORD_SCHEMA,
        "ok": not failures,
        "replay_preserves_revision_hashes": not failures,
        "failures": failures,
        "manifest_hash": stored_m,
        "revision_count": len(revisions),
        **neutral_flags(),
    }
    record["replay_hash"] = canonical_hash({"manifest_hash": stored_m, "failures": failures})
    return record
