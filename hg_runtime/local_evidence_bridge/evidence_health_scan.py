"""LEB-6 evidence health scan.

Produces AIS-style record-health findings over local evidence receipts. A
finding is an observation, never authority. Redaction-flagged receipts raise a
higher-severity health signal.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_evidence_health_finding(*, finding_id: str, receipt: dict) -> dict:
    flagged = bool(receipt.get("secret_like_content_redacted"))
    finding = {
        "schema_version": "1",
        "record_type": "evidence_health_finding_v1",
        "finding_id": finding_id,
        "source_component": "local_evidence_bridge",
        "signal_type": "evidence_redaction_flagged" if flagged else "evidence_receipt_observed",
        "severity": "YELLOW" if flagged else "WATCH",
        "evidence_ref": receipt.get("receipt_id", "unknown"),
        "evidence_receipt_hash": receipt.get("receipt_hash", ""),
        "finding_is_authority": False,
        "repair_recommendation_is_patch_permission": False,
        "local_evidence_is_authoritative": False,
        **neutral_flags(),
    }
    finding["record_hash"] = record_hash(finding)
    assert_neutral(finding)
    return finding


def build_evidence_health_findings(receipts: list[dict]) -> list[dict]:
    return [
        build_evidence_health_finding(finding_id=f"evh-{i:03d}", receipt=r)
        for i, r in enumerate(sorted(receipts, key=lambda x: x.get("receipt_id", "")), start=1)
    ]
