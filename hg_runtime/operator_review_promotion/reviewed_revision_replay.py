"""ORP-4 reviewed local belief revision replay."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import OperatorReviewPromotionError, assert_neutral, neutral_flags, record_hash


def replay_reviewed_revision(run: dict, manifest: dict) -> dict:
    failures: list[str] = []
    groups = [
        ("reviewed_belief_state_hashes", run["reviewed_belief_states"]),
        ("reviewed_belief_revision_hashes", run["reviewed_belief_revisions"]),
        ("reviewed_contradiction_hashes", run["reviewed_local_contradictions"]),
        ("reviewed_provenance_chain_hashes", run["reviewed_local_provenance_chains"]),
    ]
    for key, rows in groups:
        if [row["record_hash"] for row in rows] != manifest.get(key, []):
            failures.append(f"{key}_mismatch")
        for row in rows:
            if row["record_hash"] != record_hash(row):
                failures.append(f"record_hash_mismatch:{row.get('record_type')}")
    try:
        for _, rows in groups:
            for row in rows:
                assert_neutral(row)
        assert_neutral(manifest)
    except OperatorReviewPromotionError as exc:
        failures.append(f"boundary_violation:{exc}")
    replay = {
        "schema_version": "1",
        "record_type": "operator_review_replay_record_v1",
        "replay_id": "orp4-reviewed-local-belief-revision-replay",
        "replay_preserves_reviewed_revision_hashes": not failures,
        "receipt_chain_root": record_hash({"records": [record_hash(r) for _, rows in groups for r in rows] + [manifest["manifest_hash"]]}),
        "failures": failures,
        **neutral_flags(),
    }
    replay["record_hash"] = record_hash(replay)
    return replay
