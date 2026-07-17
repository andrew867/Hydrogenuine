"""LEB-2 links local evidence receipts to reviewable WMBR claim inputs."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.evidence_contradiction_record import build_contradiction_record
from hg_runtime.local_evidence_bridge.evidence_support_record import build_support_record
from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, assert_neutral, neutral_flags, record_hash

VALID_LINK_KINDS = {"SUPPORT_CANDIDATE", "CONTRADICTION_CANDIDATE"}


def build_evidence_claim_link(*, link_id: str, receipt: dict, claim_id: str, link_kind: str) -> dict:
    if link_kind not in VALID_LINK_KINDS:
        raise EvidenceBridgeError(f"invalid_link_kind:{link_kind}")
    link = {
        "schema_version": "1",
        "record_type": "evidence_claim_link_v1",
        "link_id": link_id,
        "claim_id": claim_id,
        "evidence_receipt_id": receipt["receipt_id"],
        "evidence_receipt_hash": receipt["receipt_hash"],
        "link_kind": link_kind,
        "support_link_is_not_proof": True,
        "contradiction_link_is_not_truth_resolution": True,
        "evidence_receipt_is_not_automatic_belief_revision": True,
        "wmbr03_ledger_mutated": False,
        "reviewable_input_only": True,
        **neutral_flags(),
    }
    link["record_hash"] = record_hash(link)
    assert_neutral(link)
    return link


def build_claim_bridge(receipts: list[dict]) -> dict:
    if len(receipts) < 2:
        raise EvidenceBridgeError("at_least_two_fixture_receipts_required")
    support_link = build_evidence_claim_link(
        link_id="leb2-link-support-001",
        receipt=receipts[0],
        claim_id="wmbr-fixture-claim-local-evidence-supported",
        link_kind="SUPPORT_CANDIDATE",
    )
    contradiction_link = build_evidence_claim_link(
        link_id="leb2-link-contradiction-001",
        receipt=receipts[1],
        claim_id="wmbr-fixture-claim-local-evidence-contested",
        link_kind="CONTRADICTION_CANDIDATE",
    )
    links = [support_link, contradiction_link]
    supports = [build_support_record(link_id=support_link["link_id"], receipt=receipts[0], claim_id=support_link["claim_id"])]
    contradictions = [
        build_contradiction_record(
            link_id=contradiction_link["link_id"],
            receipt=receipts[1],
            claim_id=contradiction_link["claim_id"],
        )
    ]
    return {"links": links, "supports": supports, "contradictions": contradictions}
