"""REB-RESTORE-LIVE continuity refusal/compensation — no live restore."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.reb_restore_live.errors import REB_COMPENSATION_RECORDED, REB_CONTINUITY_REFUSAL_RECORDED
from hg_core.reb_restore_live.no_authority import advisory_only_marker
from hg_runtime.live_reentry_restore.types import FIXTURE_CLOCK, ContinuityRefusalRecord, RestoreReceipt


def _refusal_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "continuity_refusal"})
    return f"reb-ref-{digest.rsplit(':', 1)[-1][:12]}"


def _compensation_id(refusal_id: str) -> str:
    digest = canonical_hash({"refusal_id": refusal_id, "kind": "compensation"})
    return f"reb-cmp-{digest.rsplit(':', 1)[-1][:12]}"


def continuity_refusal_record(
    receipt: RestoreReceipt, *, continuity_claim_ref: str, observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    record = ContinuityRefusalRecord(
        refusal_id=_refusal_id(receipt.receipt_id), receipt_id=receipt.receipt_id,
        request_id=receipt.request_id, continuity_claim_ref=continuity_claim_ref, observed_at=observed_at,
    )
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": REB_CONTINUITY_REFUSAL_RECORDED,
        "continuity_refusal_record": record.to_payload(), "live_restore_performed": False,
        "permission_granted": False, "observed_at": observed_at,
    }


def compensation_record(
    refusal_record: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    refusal_id = str(refusal_record.get("refusal_id", ""))
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": REB_COMPENSATION_RECORDED,
        "compensation_record": {
            "compensation_id": _compensation_id(refusal_id), "refusal_id": refusal_id,
            "observed_at": observed_at, "permission_granted": False, "authority_created": False,
            "live_restore_performed": False,
        },
        "live_restore_performed": False, "permission_granted": False, "observed_at": observed_at,
    }


__all__ = ["compensation_record", "continuity_refusal_record"]
