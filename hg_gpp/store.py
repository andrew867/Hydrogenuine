"""In-memory permit store — expiry/revocation tracking plus single-use consume.

Slice 2 (2026-07-03): `consume()` enforces exactly-once permit use at the dispatch
boundary. It is a lock-guarded check-and-set so double-consume is deterministic:
the first caller wins, every later caller gets `already_consumed`. Consumption is
recorded as a hashed `PermitConsumeReceipt`. Nothing in GPP issuance or
verification calls `consume()` — the dispatch layer owns that boundary.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.time.expiry import is_expired

from hg_gpp.models import GovernedPermit, PermitRevocation

CONSUME_RECEIPT_SCHEMA = "gpp-permit-consume-receipt"
CONSUME_RECEIPT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class PermitConsumeReceipt:
    permit_id: str
    permit_hash: str
    consumed_at: str
    consumed_by: str
    handoff_ref: str
    request_id: str
    receipt_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "receipt_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": CONSUME_RECEIPT_SCHEMA,
            "schema_version": CONSUME_RECEIPT_SCHEMA_VERSION,
            "permit_id": self.permit_id,
            "permit_hash": self.permit_hash,
            "consumed_at": self.consumed_at,
            "consumed_by": self.consumed_by,
            "handoff_ref": self.handoff_ref,
            "request_id": self.request_id,
        }
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


@dataclass(frozen=True)
class ConsumeResult:
    ok: bool
    reason: str
    receipt: Optional[PermitConsumeReceipt] = None


class PermitStore:
    def __init__(self) -> None:
        self._permits: dict[str, GovernedPermit] = {}
        self._revocations: dict[str, PermitRevocation] = {}
        self._execution_log: list[str] = []
        self._consumed: dict[str, PermitConsumeReceipt] = {}
        self._consume_lock = threading.Lock()

    def put(self, permit: GovernedPermit) -> None:
        self._permits[permit.permit_id] = permit

    def get(self, permit_id: str) -> Optional[GovernedPermit]:
        return self._permits.get(permit_id)

    def revoke(self, revocation: PermitRevocation) -> bool:
        permit = self._permits.get(revocation.permit_id)
        if permit is None:
            return False
        self._revocations[revocation.permit_id] = revocation
        updated = GovernedPermit(
            permit_id=permit.permit_id,
            request_id=permit.request_id,
            subject_id=permit.subject_id,
            agent_id=permit.agent_id,
            operator_ref=permit.operator_ref,
            authority_chain_ref=permit.authority_chain_ref,
            requested_action_type=permit.requested_action_type,
            scope=permit.scope,
            evidence_refs=permit.evidence_refs,
            proof_bundle_refs=permit.proof_bundle_refs,
            identity_ref=permit.identity_ref,
            admission_ref=permit.admission_ref,
            freshness_ref=permit.freshness_ref,
            redaction_ref=permit.redaction_ref,
            retention_ref=permit.retention_ref,
            capability_ref=permit.capability_ref,
            risk_class=permit.risk_class,
            issued_at=permit.issued_at,
            expires_at=permit.expires_at,
            status="revoked",
            deny_reasons=permit.deny_reasons,
            revoked_at=revocation.revoked_at,
            permit_kind=permit.permit_kind,
        )
        self._permits[permit.permit_id] = updated
        return True

    def is_revoked(self, permit_id: str) -> bool:
        return permit_id in self._revocations

    def revocation(self, permit_id: str) -> Optional[PermitRevocation]:
        return self._revocations.get(permit_id)

    def is_expired(self, permit: GovernedPermit, now: str) -> bool:
        return is_expired(permit.expires_at, now)

    def record_execution_attempt(self, permit_id: str) -> None:
        """Test hook — GPP must never call this."""
        self._execution_log.append(permit_id)

    @property
    def execution_log(self) -> list[str]:
        return list(self._execution_log)

    def consume(self, permit_id: str, *, now: str, consumed_by: str,
                handoff_ref: str = "") -> ConsumeResult:
        """Consume a permit exactly once. Deterministic under contention.

        Rejection ordering (checked inside the lock): unknown → revoked →
        expired → already_consumed. Only a granted, live, never-consumed
        permit consumes; the winning caller gets the hashed consume receipt.
        """
        with self._consume_lock:
            permit = self._permits.get(permit_id)
            if permit is None:
                return ConsumeResult(False, "unknown_permit")
            if permit_id in self._revocations or permit.status == "revoked":
                return ConsumeResult(False, "revoked")
            if is_expired(permit.expires_at, now):
                return ConsumeResult(False, "expired")
            if permit_id in self._consumed:
                return ConsumeResult(False, "already_consumed")
            if permit.status != "granted":
                return ConsumeResult(False, f"not_granted:{permit.status}")
            receipt = PermitConsumeReceipt(
                permit_id=permit_id,
                permit_hash=permit.permit_hash,
                consumed_at=now,
                consumed_by=consumed_by,
                handoff_ref=handoff_ref,
                request_id=permit.request_id,
            )
            self._consumed[permit_id] = receipt
            return ConsumeResult(True, "consumed", receipt)

    def is_consumed(self, permit_id: str) -> bool:
        return permit_id in self._consumed

    def consume_count(self, permit_id: str) -> int:
        return 1 if permit_id in self._consumed else 0

    def consume_receipt(self, permit_id: str) -> Optional[PermitConsumeReceipt]:
        return self._consumed.get(permit_id)


__all__ = ["ConsumeResult", "PermitConsumeReceipt", "PermitStore"]
