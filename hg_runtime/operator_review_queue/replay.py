"""Replay validation for Phase 41 queue and dry-run receipts."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash


def replay_records(records: list[dict]) -> dict:
    head = "sha256:phase41_genesis"
    failures: list[str] = []
    for index, row in enumerate(records):
        if row.get("previous_hash") != head:
            failures.append(f"chain_break:{index}")
        payload = row.get("payload", {})
        if canonical_hash(payload) != row.get("payload_hash"):
            failures.append(f"payload_hash_mismatch:{index}")
        expected = dict(row)
        expected.pop("chain_hash", None)
        if canonical_hash(expected) != row.get("chain_hash"):
            failures.append(f"chain_hash_mismatch:{index}")
        if payload.get("schema") == "operator_permit_fixture_v1" and payload.get("issuer_is_agent_zero"):
            failures.append("self_issued_permit_in_replay")
        if payload.get("schema") == "patch_apply_dry_run_result_v1" and payload.get("live_repo_mutated"):
            failures.append("live_repo_mutated_in_replay")
        head = row.get("chain_hash", "")
    return {"ok": not failures, "failures": failures, "chain_root": head, "record_count": len(records)}
