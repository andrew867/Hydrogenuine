"""LEB-3 local revision replay."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import neutral_flags, record_hash


def replay_local_revision(run: dict, manifest: dict) -> dict:
    failures: list[str] = []
    groups = [
        ("belief_state_hashes", run["belief_states"]),
        ("belief_revision_hashes", run["belief_revisions"]),
        ("contradiction_hashes", run["local_contradictions"]),
        ("provenance_chain_hashes", run["provenance_chains"]),
    ]
    for key, rows in groups:
        if [row["record_hash"] for row in rows] != manifest.get(key, []):
            failures.append(f"{key}_mismatch")
        for row in rows:
            expected = record_hash({k: v for k, v in row.items() if k != "record_hash"})
            if row["record_hash"] != expected:
                failures.append(f"record_hash_mismatch:{row.get('record_type')}:{row.get('claim_id')}")
    return {
        "schema_version": "1",
        "record_type": "local_revision_replay_record_v1",
        "replay_id": "leb3-local-revision-replay",
        "replay_preserves_local_revision_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }
