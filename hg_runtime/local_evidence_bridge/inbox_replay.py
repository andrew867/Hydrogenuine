"""LEB-4 operator inbox replay.

Recomputes accepted/rejected record hashes and confirms the manifest hash lists
are preserved deterministically. Asserts no forbidden boundary flag flipped true.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_inbox_run_manifest(policy: dict, manifest: dict, accepted: list[dict], rejected: list[dict]) -> dict:
    run = {
        "schema_version": "1",
        "record_type": "operator_inbox_run_manifest_v1",
        "manifest_id": "leb4-operator-inbox-run-manifest",
        "policy_hash": policy["record_hash"],
        "source_manifest_hash": manifest["manifest_hash"],
        "allowed_root": policy["allowed_root"],
        "operator_inbox_enabled": policy["operator_inbox_enabled"],
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted_hashes": [r["record_hash"] for r in accepted],
        "rejected_hashes": [r["record_hash"] for r in rejected],
        **neutral_flags(),
    }
    run["manifest_hash"] = record_hash(run)
    assert_neutral(run)
    return run


def replay_inbox(accepted: list[dict], rejected: list[dict], run_manifest: dict) -> dict:
    failures: list[str] = []
    if [r["record_hash"] for r in accepted] != run_manifest.get("accepted_hashes", []):
        failures.append("accepted_hash_list_mismatch")
    if [r["record_hash"] for r in rejected] != run_manifest.get("rejected_hashes", []):
        failures.append("rejected_hash_list_mismatch")
    for record in accepted + rejected:
        expected = record_hash({k: v for k, v in record.items() if k != "record_hash"})
        if record["record_hash"] != expected:
            failures.append(f"record_hash_mismatch:{record.get('source_id')}")
    try:
        for record in accepted + rejected:
            assert_neutral(record)
        assert_neutral(run_manifest)
    except EvidenceBridgeError as exc:
        failures.append(f"boundary_violation:{exc}")
    return {
        "schema_version": "1",
        "record_type": "operator_inbox_replay_v1",
        "replay_id": "leb4-operator-inbox-replay",
        "replay_preserves_inbox_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }
