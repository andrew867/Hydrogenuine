"""PUB-EXT-LIVE withdrawal/compensation — no live external action."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.pub_ext_live.errors import PUB_EXT_COMPENSATION_RECORDED, PUB_EXT_WITHDRAWAL_RECORDED
from hg_core.pub_ext_live.no_authority import advisory_only_marker
from hg_runtime.live_publication_external.types import (
    FIXTURE_CLOCK, CompensationRecord, PublicationReceipt, WithdrawalRecord,
)


def _withdrawal_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "withdrawal"})
    return f"pub-wdr-{digest.rsplit(':', 1)[-1][:12]}"


def _compensation_id(withdrawal_id: str) -> str:
    digest = canonical_hash({"withdrawal_id": withdrawal_id, "kind": "compensation"})
    return f"pub-cmp-{digest.rsplit(':', 1)[-1][:12]}"


def withdrawal_record(
    receipt: PublicationReceipt, *, content_digest: str, observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    record = WithdrawalRecord(
        withdrawal_id=_withdrawal_id(receipt.receipt_id), receipt_id=receipt.receipt_id,
        request_id=receipt.request_id, content_digest=content_digest, observed_at=observed_at,
    )
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": PUB_EXT_WITHDRAWAL_RECORDED,
        "withdrawal_record": record.to_payload(), "published": False, "live_external_action": False,
        "permission_granted": False, "observed_at": observed_at,
    }


def compensation_record(
    withdrawal_record_dict: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    withdrawal_id = str(withdrawal_record_dict.get("withdrawal_id", ""))
    content_digest = str(withdrawal_record_dict.get("content_digest", ""))
    record = CompensationRecord(
        compensation_id=_compensation_id(withdrawal_id), withdrawal_id=withdrawal_id,
        content_digest=content_digest, observed_at=observed_at,
    )
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": PUB_EXT_COMPENSATION_RECORDED,
        "compensation_record": record.to_payload(), "published": False, "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["compensation_record", "withdrawal_record"]
