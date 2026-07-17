"""ORP-1 decision ledger record builders."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.decision import (
    build_operator_deferral_record,
    build_operator_rejection_record,
    build_operator_review_decision,
    build_reviewed_evidence_link,
)
from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash

LEDGER_STATUSES = (
    "APPROVE_FOR_PROVISIONAL_USE",
    "REJECT_SOURCE",
    "DEFER_REVIEW",
    "REQUEST_MORE_EVIDENCE",
    "QUARANTINE_RECOMMENDED",
    "RETRACTION_RECOMMENDED",
)


def build_decisions_from_tasks(review_tasks: list[dict]) -> list[dict]:
    decisions: list[dict] = []
    for index, status in enumerate(LEDGER_STATUSES, start=1):
        task = review_tasks[(index - 1) % len(review_tasks)]
        decisions.append(
            build_operator_review_decision(
                decision_id=f"orp1-decision-{index:03d}",
                review_task=task,
                status=status,
                rationale=f"orp1_fixture_{status.lower()}",
            )
        )
    return decisions


def build_review_links(decisions: list[dict]) -> list[dict]:
    return [build_reviewed_evidence_link(link_id=f"orp1-reviewed-link-{i:03d}", decision=d) for i, d in enumerate(decisions, start=1)]


def build_rejection_records(decisions: list[dict]) -> list[dict]:
    return [
        build_operator_rejection_record(rejection_id=f"orp1-rejection-{i:03d}", decision=d)
        for i, d in enumerate([d for d in decisions if d["decision_status"] == "REJECT_SOURCE"], start=1)
    ]


def build_deferral_records(decisions: list[dict]) -> list[dict]:
    return [
        build_operator_deferral_record(deferral_id=f"orp1-deferral-{i:03d}", decision=d)
        for i, d in enumerate([d for d in decisions if d["decision_status"] == "DEFER_REVIEW"], start=1)
    ]


def build_operator_review_manifest(*, decisions: list[dict], links: list[dict], inputs: dict) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "operator_review_manifest_v1",
        "manifest_id": "orp1-operator-review-decision-ledger-manifest",
        "append_only": True,
        "source_leb5_manifest_hash": inputs["leb5_manifest"]["manifest_hash"],
        "source_leb6_manifest_hash": inputs["leb6_manifest"]["manifest_hash"],
        "source_leb7_manifest_hash": inputs["leb7_manifest"]["manifest_hash"],
        "leb5_review_task_count": len(inputs["leb5_review_tasks"]),
        "leb6_health_finding_count": len(inputs["leb6_health_findings"]),
        "leb6_quarantine_candidate_count": len(inputs["leb6_quarantine_candidates"]),
        "leb6_security_finding_count": len(inputs["leb6_security_findings"]),
        "leb7_retraction_count": len(inputs["leb7_retractions"]),
        "leb7_quarantine_count": len(inputs["leb7_quarantines"]),
        "decision_count": len(decisions),
        "reviewed_link_count": len(links),
        "decision_hashes": [d["decision_hash"] for d in decisions],
        "reviewed_link_hashes": [l["record_hash"] for l in links],
        "original_evidence_preserved": True,
        "operator_review_ledger_is_append_only": True,
        "approval_proves_evidence": False,
        "approval_authorizes_action": False,
        "approval_authorizes_tools": False,
        "approval_authorizes_web": False,
        "approval_authorizes_providers": False,
        "rejection_deletes_source": False,
        "deferral_remains_open": True,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
