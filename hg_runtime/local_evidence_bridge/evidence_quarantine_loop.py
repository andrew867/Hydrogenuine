"""LEB-7 evidence quarantine loop (append-only).

An evidence quarantine is not deletion: the original receipt is preserved and a
review task is required. Quarantine is metadata only and is never enforced as an
automatic side effect.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.evidence_decay import build_evidence_decay_record
from hg_runtime.local_evidence_bridge.evidence_retention_policy import (
    DECAY_CONDITIONS,
    QUARANTINE_CONDITIONS,
    RETRACTABLE_CONDITIONS,
    build_retention_policy,
)
from hg_runtime.local_evidence_bridge.evidence_retraction import build_evidence_retraction_record
from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    assert_neutral,
    neutral_flags,
    record_hash,
)

VERDICT_GREEN = "GREEN_LEB_7_EVIDENCE_RETRACTION_QUARANTINE_LOOP"
VERDICT_RED = "RED_LEB_7_EVIDENCE_RETRACTION_QUARANTINE_FAILED"


def build_evidence_quarantine_record(*, quarantine_id: str, receipt: dict, reason: str, retraction_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "evidence_quarantine_record_v1",
        "quarantine_id": quarantine_id,
        "original_ref": receipt.get("receipt_id", "unknown"),
        "original_receipt_hash": receipt.get("receipt_hash", ""),
        "reason": reason,
        "source_retraction_id": retraction_id,
        "review_task_id": f"qrt-{quarantine_id}",
        "evidence_quarantine_is_deletion": False,
        "original_receipt_preserved": True,
        "deletion_performed": False,
        "rewrite_performed": False,
        "auto_quarantine_enforced": False,
        "review_required": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_loop_fixture_receipts() -> list[dict]:
    """Deterministic receipts spanning every retention condition plus a clean one."""
    conditions = ["CLEAN", "BAD", "SUSPECT", "STALE", "CONTRADICTED", "REDACTION_FAILED"]
    receipts: list[dict] = []
    for i, cond in enumerate(conditions, start=1):
        receipt = {
            "schema_version": "1",
            "record_type": "local_evidence_receipt_v1",
            "receipt_id": f"ev-loop-{i:03d}-{cond.lower()}",
            "evidence_condition": cond,
        }
        receipt["receipt_hash"] = record_hash(receipt)
        receipts.append(receipt)
    return receipts


def build_retraction_quarantine_loop(receipts: list[dict]) -> dict:
    """Walk receipts and append retraction/quarantine/decay records for bad ones.

    Nothing is deleted: clean receipts are untouched; flagged receipts get an
    append-only retraction (with review requirement) and either a quarantine or a
    decay record. Original receipts are always preserved.
    """
    policy = build_retention_policy()
    retractions: list[dict] = []
    quarantines: list[dict] = []
    decays: list[dict] = []

    for i, receipt in enumerate(sorted(receipts, key=lambda r: r.get("receipt_id", "")), start=1):
        condition = receipt.get("evidence_condition", "CLEAN")
        if condition not in RETRACTABLE_CONDITIONS:
            continue
        retraction = build_evidence_retraction_record(
            retraction_id=f"evret-{i:03d}", receipt=receipt, reason=condition
        )
        retractions.append(retraction)
        if condition in QUARANTINE_CONDITIONS:
            quarantines.append(
                build_evidence_quarantine_record(
                    quarantine_id=f"evq-{i:03d}", receipt=receipt, reason=condition,
                    retraction_id=retraction["retraction_id"],
                )
            )
        elif condition in DECAY_CONDITIONS:
            decays.append(
                build_evidence_decay_record(
                    decay_id=f"evdec-{i:03d}", receipt=receipt, retraction_id=retraction["retraction_id"]
                )
            )

    manifest = {
        "schema_version": "1",
        "record_type": "retraction_quarantine_manifest_v1",
        "manifest_id": "leb7-retraction-quarantine-manifest",
        "policy_hash": policy["record_hash"],
        "input_receipt_count": len(receipts),
        "retraction_count": len(retractions),
        "quarantine_count": len(quarantines),
        "decay_count": len(decays),
        "retraction_hashes": [r["record_hash"] for r in retractions],
        "quarantine_hashes": [q["record_hash"] for q in quarantines],
        "decay_hashes": [d["record_hash"] for d in decays],
        "append_only": True,
        "original_receipts_preserved": True,
        "retraction_creates_review_requirement": all(r["review_required"] for r in retractions),
        "derived_belief_revisions_auditable": True,
        "deletion_performed": False,
        "erasure_performed": False,
        "auto_quarantine_enforced": False,
        "automatic_patching_enabled": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)

    replay = replay_retraction_quarantine(retractions, quarantines, decays, manifest)
    return {
        "policy": policy,
        "retractions": retractions,
        "quarantines": quarantines,
        "decays": decays,
        "manifest": manifest,
        "replay": replay,
    }


def replay_retraction_quarantine(retractions, quarantines, decays, manifest) -> dict:
    failures: list[str] = []
    checks = [
        ([r["record_hash"] for r in retractions], manifest.get("retraction_hashes", []), "retraction_hash_mismatch"),
        ([q["record_hash"] for q in quarantines], manifest.get("quarantine_hashes", []), "quarantine_hash_mismatch"),
        ([d["record_hash"] for d in decays], manifest.get("decay_hashes", []), "decay_hash_mismatch"),
    ]
    for computed, stored, label in checks:
        if computed != stored:
            failures.append(label)
    for record in [*retractions, *quarantines, *decays]:
        expected = record_hash({k: v for k, v in record.items() if k != "record_hash"})
        if record["record_hash"] != expected:
            failures.append("record_hash_mismatch")
    try:
        for record in [*retractions, *quarantines, *decays, manifest]:
            assert_neutral(record)
    except EvidenceBridgeError as exc:
        failures.append(f"boundary_violation:{exc}")
    return {
        "schema_version": "1",
        "record_type": "retraction_quarantine_replay_v1",
        "replay_id": "leb7-retraction-quarantine-replay",
        "replay_preserves_loop_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }


def validate_leb7_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "retention_policy_written": "retention_policy_required",
        "retraction_records_written": "retraction_records_required",
        "quarantine_records_written": "quarantine_records_required",
        "decay_records_written": "decay_records_required",
        "manifest_written": "manifest_required",
        "evidence_retraction_not_erasure": "retraction_erasure_boundary",
        "evidence_quarantine_not_deletion": "quarantine_deletion_boundary",
        "evidence_decay_not_deletion": "decay_deletion_boundary",
        "original_receipt_preserved": "original_preservation_boundary",
        "derived_belief_revisions_auditable": "belief_revision_audit_boundary",
        "retraction_creates_review_requirement": "review_requirement_boundary",
        "append_only": "append_only_required",
        "no_deletion": "deletion_forbidden",
        "no_erasure": "erasure_forbidden",
        "no_automatic_patching": "automatic_patching_forbidden",
        "no_auto_quarantine_enforcement": "auto_quarantine_forbidden",
        "replay_preserves_loop_hashes": "replay_required",
        "secret_redaction_passed": "secret_redaction_required",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
    }
    for key, failure in checks.items():
        if not result.get(key):
            failures.append(failure)
    for key in (
        "deletion_performed",
        "erasure_performed",
        "auto_quarantine_enforced",
        "automatic_patching_enabled",
        "truth_claimed",
        "tools_authorized",
        "authority_granted",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
