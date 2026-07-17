"""LEB-5 evidence review queue.

Builds operator review tasks from local evidence receipts and LEB outputs.
Evidence receipts do NOT directly mutate belief states without review policy: the
queue creates review tasks, not actions. Suspicious evidence recommends a
quarantine *candidate* (metadata only). High fever restricts the review flow.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.review_policy import build_review_policy, classify_target
from hg_runtime.local_evidence_bridge.review_task import build_review_task
from hg_runtime.local_evidence_bridge.schemas import (
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_fixture_targets(root) -> list[dict]:
    """Deterministic review targets drawn from real LEB-1/LEB-2 fixtures.

    Includes a clean receipt (ordinary review), a contradiction link
    (quarantine candidate), and a redaction-flagged receipt (quarantine
    candidate) so the queue exercises both review and quarantine-candidate paths.
    """
    from hg_runtime.local_evidence_bridge.claim_linker import build_claim_bridge
    from hg_runtime.local_evidence_bridge.text_ingestion import ingest_text_source

    paths = ["tests/fixtures/local_evidence/source_001.md", "tests/fixtures/local_evidence/source_002.txt"]
    rows = [ingest_text_source(root, p, source_id=f"src-{i}") for i, p in enumerate(paths, start=1)]
    receipts = [r["evidence_receipt"] for r in rows]
    bridge = build_claim_bridge(receipts)
    links = bridge["links"]

    redaction_flagged = dict(receipts[0])
    redaction_flagged["receipt_id"] = "ev-redaction-flagged"
    redaction_flagged["secret_like_content_redacted"] = True
    redaction_flagged["receipt_hash"] = record_hash(
        {k: v for k, v in redaction_flagged.items() if k != "receipt_hash"}
    )

    return [receipts[1], *links, redaction_flagged]


VERDICT_GREEN = "GREEN_LEB_5_EVIDENCE_REVIEW_QUEUE"
VERDICT_RED = "RED_LEB_5_EVIDENCE_REVIEW_QUEUE_FAILED"


def validate_leb5_gate(result: dict) -> dict:
    failures: list[str] = []
    checks = {
        "review_tasks_written": "review_tasks_required",
        "review_manifest_written": "review_manifest_required",
        "review_policy_written": "review_policy_required",
        "review_task_not_action": "review_task_action_boundary",
        "review_task_not_belief_promotion": "review_task_belief_boundary",
        "review_task_not_tool_authorization": "review_task_tool_boundary",
        "review_task_not_operator_approval": "review_task_approval_boundary",
        "suspicious_recommends_quarantine_candidate": "quarantine_candidate_required",
        "high_fever_restricts_review_flow": "fever_restriction_required",
        "no_automatic_patching": "automatic_patching_forbidden",
        "no_deletion": "deletion_forbidden",
        "replay_preserves_review_hashes": "replay_required",
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
        "review_task_treated_as_action",
        "review_task_treated_as_approval",
        "automatic_belief_promotion",
        "automatic_patching_enabled",
        "deletion_performed",
        "web_browse_performed",
        "external_provider_calls_made",
        "live_external_side_effects_created",
        "tools_authorized",
        "authority_granted",
        "fever_unlocks_action",
    ):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}


def _target_key(record: dict) -> str:
    for key in ("receipt_id", "link_id", "belief_state_id", "revision_id", "contradiction_id"):
        if key in record:
            return record[key]
    return record.get("record_type", "unknown")


def build_review_queue(*, targets: list[dict], fever_level: str = "NORMAL") -> dict:
    """Build the review queue over a deterministic list of target records."""
    policy = build_review_policy(fever_level=fever_level)
    restricted = policy["review_flow_restricted"]

    tasks: list[dict] = []
    for index, target in enumerate(sorted(targets, key=_target_key), start=1):
        recommended_action, reason = classify_target(target)
        tasks.append(
            build_review_task(
                task_id=f"review-task-{index:03d}",
                target=target,
                recommended_action=recommended_action,
                reason=reason,
                fever_level=fever_level,
                restricted=restricted,
            )
        )

    quarantine_candidates = [t for t in tasks if t["quarantine_candidate"]]
    manifest = {
        "schema_version": "1",
        "record_type": "evidence_review_manifest_v1",
        "manifest_id": "leb5-evidence-review-manifest",
        "policy_hash": policy["record_hash"],
        "fever_level": fever_level,
        "review_flow_restricted": restricted,
        "task_count": len(tasks),
        "quarantine_candidate_count": len(quarantine_candidates),
        "task_hashes": [t["record_hash"] for t in tasks],
        "review_task_is_action": False,
        "review_task_is_belief_promotion": False,
        "review_task_is_operator_approval": False,
        "review_task_is_tool_authorization": False,
        "automatic_patching_enabled": False,
        "deletion_enabled": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return {"policy": policy, "tasks": tasks, "manifest": manifest}
