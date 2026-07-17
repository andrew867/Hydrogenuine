"""GMG-LIVE revocation — revocation and expiry records; no live grants."""

from __future__ import annotations

from typing import Any

from hg_core.gmg_live.errors import GMG_EXPIRY_RECORDED, GMG_REVOCATION_RECORDED
from hg_core.gmg_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.grant_authority_live.types import (
    FIXTURE_CLOCK,
    GrantAuditRecord,
    GrantExpiryRecord,
    GrantReceipt,
    GrantRevocation,
)


def _revocation_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "revocation"})
    return f"gmg-rev-{digest.rsplit(':', 1)[-1][:12]}"


def _expiry_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "expiry"})
    return f"gmg-exp-{digest.rsplit(':', 1)[-1][:12]}"


def _audit_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "audit"})
    return f"gmg-aud-{digest.rsplit(':', 1)[-1][:12]}"


def revoke_grant(
    receipt: GrantReceipt,
    *,
    grant_target: str,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record grant revocation; no live grant effect."""
    record = GrantRevocation(
        revocation_id=_revocation_id(receipt.receipt_id),
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        grant_type=receipt.grant_type,
        grant_target=grant_target,
        observed_at=observed_at,
    )
    audit = GrantAuditRecord(
        audit_id=_audit_id(receipt.receipt_id),
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        grant_type=receipt.grant_type,
        reason_code=GMG_REVOCATION_RECORDED,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": GMG_REVOCATION_RECORDED,
        "revocation_record": record.to_payload(),
        "audit_record": audit.to_payload(),
        "revocation_acknowledged": True,
        "live_grant_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def record_grant_expiry(
    receipt: GrantReceipt,
    *,
    grant_target: str,
    grant_expires_at: str,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record grant expiry; no live grant effect."""
    record = GrantExpiryRecord(
        expiry_id=_expiry_id(receipt.receipt_id),
        receipt_id=receipt.receipt_id,
        grant_type=receipt.grant_type,
        grant_target=grant_target,
        grant_expires_at=grant_expires_at,
        observed_at=observed_at,
    )
    audit = GrantAuditRecord(
        audit_id=_audit_id(receipt.receipt_id),
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        grant_type=receipt.grant_type,
        reason_code=GMG_EXPIRY_RECORDED,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": GMG_EXPIRY_RECORDED,
        "expiry_record": record.to_payload(),
        "audit_record": audit.to_payload(),
        "live_grant_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["record_grant_expiry", "revoke_grant"]
