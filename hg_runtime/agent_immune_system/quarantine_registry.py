"""AIS-3 append-only quarantine registry."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.quarantine import build_quarantine_record, validate_quarantine_record
from hg_runtime.agent_immune_system.quarantine_policy import validate_quarantine_policy
from hg_runtime.agent_immune_system.quarantine_review import build_quarantine_review_task
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags


def quarantine_fixtures() -> list[dict]:
    return [
        {
            "quarantine_id": "q-suspect-proof-bundle",
            "artifact_type": "proof_bundle",
            "original_ref": "docs/proofs/autonomous_agent_zero/SUSPECT/fixture",
            "content_hash": "fixture-proof-hash",
            "reason": "suspect_proof_bundle",
            "review_task_id": "qrt-suspect-proof-bundle",
        },
        {
            "quarantine_id": "q-suspect-module",
            "artifact_type": "module",
            "original_ref": "hg_runtime/fixture/suspect_module.py",
            "content_hash": "fixture-module-hash",
            "reason": "suspect_module",
            "review_task_id": "qrt-suspect-module",
        },
        {
            "quarantine_id": "q-generated-artifact",
            "artifact_type": "generated_artifact",
            "original_ref": "docs/proofs/autonomous_agent_zero/GENERATED/fixture.json",
            "content_hash": "fixture-artifact-hash",
            "reason": "suspect_generated_artifact",
            "review_task_id": "qrt-generated-artifact",
        },
        {
            "quarantine_id": "q-external-effect-path",
            "artifact_type": "external_effect_path",
            "original_ref": "fixtures/ais/external_effect_path",
            "content_hash": "fixture-external-effect-hash",
            "reason": "suspect_external_effect_path",
            "review_task_id": "qrt-external-effect-path",
        },
        {
            "quarantine_id": "q-false-positive",
            "artifact_type": "false_positive",
            "original_ref": "fixtures/ais/false_positive",
            "content_hash": "fixture-false-positive-hash",
            "reason": "false_positive_requires_review",
            "review_task_id": "qrt-false-positive",
        },
    ]


def build_quarantine_manifest(records: list[dict], review_tasks: list[dict]) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "quarantine_manifest_v1",
        "manifest_id": "ais3-quarantine-registry",
        "record_count": len(records),
        "review_task_count": len(review_tasks),
        "quarantine_record_hashes": [r["record_hash"] for r in records],
        "review_task_hashes": [r["record_hash"] for r in review_tasks],
        "append_only": True,
        "metadata_only": True,
        "originals_preserved": True,
        "review_path_required": True,
        "quarantine_is_not_deletion": True,
        "quarantine_does_not_mark_guilty": True,
        "fever_can_recommend_candidate_only": True,
        "fever_cannot_execute_deletion": True,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest


def build_quarantine_layer(fixtures: list[dict] | None = None) -> dict:
    records: list[dict] = []
    review_tasks: list[dict] = []
    for spec in fixtures or quarantine_fixtures():
        record = build_quarantine_record(**spec)
        record.update(
            {
                "append_only": True,
                "metadata_only": True,
                "original_preserved": True,
                "marked_guilty": False,
                "patch_authorized": False,
                "deletion_authorized": False,
                "phase19_hidden": False,
                "phase19_marked_green": False,
                "phase24_marked_full_green": False,
                "automatic_quarantine_enforced": False,
            }
        )
        record["record_hash"] = record_hash(record)
        validate_quarantine_record(record)
        validate_quarantine_policy(record)
        records.append(record)
        review_tasks.append(
            build_quarantine_review_task(
                review_task_id=spec["review_task_id"],
                quarantine_id=spec["quarantine_id"],
                review_reason=spec["reason"],
            )
        )

    manifest = build_quarantine_manifest(records, review_tasks)
    replay = replay_quarantine_layer(records, review_tasks, manifest)
    return {"records": records, "review_tasks": review_tasks, "manifest": manifest, "replay": replay}


def replay_quarantine_layer(records: list[dict], review_tasks: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    if [r["record_hash"] for r in records] != manifest.get("quarantine_record_hashes", []):
        failures.append("quarantine_hash_list_mismatch")
    if [r["record_hash"] for r in review_tasks] != manifest.get("review_task_hashes", []):
        failures.append("review_task_hash_list_mismatch")
    for record in records + review_tasks + [manifest]:
        try:
            validate_quarantine_policy(record)
        except Exception as exc:  # pragma: no cover - surfaced in result
            failures.append(str(exc))
    return {
        "schema_version": "1",
        "record_type": "quarantine_replay_record_v1",
        "replay_id": "ais3-quarantine-replay",
        "replay_preserves_quarantine_hash": not failures,
        "failures": failures,
        **neutral_flags(),
    }
