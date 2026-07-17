"""LEB-2 WMBR verification task link records."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import assert_neutral, neutral_flags, record_hash


def build_verification_task_links(links: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for index, link in enumerate(links, start=1):
        record = {
            "schema_version": "1",
            "record_type": "wmbr_verification_task_link_v1",
            "task_link_id": f"wmbr-task-link-{index:03d}",
            "source_link_id": link["link_id"],
            "claim_id": link["claim_id"],
            "review_task_status": "QUEUED_FOR_OPERATOR_OR_WMBR_REVIEW",
            "task_link_is_not_execution": True,
            "evidence_receipt_is_not_automatic_belief_revision": True,
            "wmbr03_ledger_mutated": False,
            "reviewable_input_only": True,
            **neutral_flags(),
        }
        record["record_hash"] = record_hash(record)
        assert_neutral(record)
        rows.append(record)
    return rows
