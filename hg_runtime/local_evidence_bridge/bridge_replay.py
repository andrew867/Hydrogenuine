"""LEB-2 deterministic bridge replay."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import neutral_flags, record_hash


def replay_wmbr_bridge(links: list[dict], supports: list[dict], contradictions: list[dict], task_links: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    groups = [
        ("link_hashes", links),
        ("support_hashes", supports),
        ("contradiction_hashes", contradictions),
        ("task_link_hashes", task_links),
    ]
    for manifest_key, rows in groups:
        if [r["record_hash"] for r in rows] != manifest.get(manifest_key, []):
            failures.append(f"{manifest_key}_mismatch")
        for row in rows:
            expected = record_hash({k: v for k, v in row.items() if k != "record_hash"})
            if row["record_hash"] != expected:
                failures.append(f"record_hash_mismatch:{row.get('record_type')}:{row.get('link_id') or row.get('task_link_id')}")
    return {
        "schema_version": "1",
        "record_type": "wmbr_bridge_replay_record_v1",
        "replay_id": "leb2-wmbr-bridge-replay",
        "replay_preserves_bridge_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }
