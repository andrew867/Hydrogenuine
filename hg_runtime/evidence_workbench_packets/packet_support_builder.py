"""Build packet support records from LEB receipts and ORP review links."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.source_summary import build_packet_support_record


def build_support_records(
    *,
    claim_id: str,
    source_id: str,
    receipt_ref: str,
    reviewed_links: list[dict],
) -> list[dict]:
    review_ref = None
    if reviewed_links:
        review_ref = f"orp:review:{reviewed_links[0]['review_decision_id']}"
    return [
        build_packet_support_record(
            support_id=f"ewp1-support-{claim_id}-{source_id}",
            claim_id=claim_id,
            source_id=source_id,
            receipt_ref=receipt_ref,
            review_decision_ref=review_ref,
        )
    ]
