"""GPP permit authority — mint governed permits; never execute."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.time.clock import get_clock

from hg_gpp.models import (
    GovernedPermit,
    PermitDecision,
    PermitDenyReason,
    PermitReceipt,
    PermitRequest,
    PermitRevocation,
)
from hg_gpp.store import PermitStore
from hg_gpp.validation import validate_permit_request

_GPP_ISSUER = "gpp:permit_authority"
_DEFAULT_TTL_S = 30.0


def _utc_now() -> str:
    return get_clock().now_utc()


def _expires_at(issued_at: str, ttl_s: float) -> str:
    issued = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    expiry = issued + timedelta(seconds=ttl_s)
    return expiry.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class PermitAuthority:
    """Governance Proof Pack runtime — evidence-only permit minting."""

    issuer_id: str = _GPP_ISSUER

    def __init__(
        self,
        *,
        store: Optional[PermitStore] = None,
        permit_ttl_s: float = _DEFAULT_TTL_S,
        clock: Any | None = None,
    ) -> None:
        self._store = store or PermitStore()
        self._permit_ttl_s = permit_ttl_s
        self._clock = clock
        self._mint_log: list[dict[str, Any]] = []
        self._oea_ter_calls: list[str] = []

    @property
    def store(self) -> PermitStore:
        return self._store

    @property
    def mint_log(self) -> list[dict[str, Any]]:
        return list(self._mint_log)

    def now(self) -> str:
        if self._clock is not None:
            return str(self._clock())
        return _utc_now()

    def issue(self, request: PermitRequest) -> PermitDecision:
        """Evaluate request and mint permit or deny — no execution."""
        now = self.now()
        deny_reasons = validate_permit_request(request, now=now, issuer_id=self.issuer_id)

        if deny_reasons:
            return self._deny(request, deny_reasons, now=now)

        issued_at = now
        expires_at = _expires_at(issued_at, self._permit_ttl_s)
        permit_id = f"gpp_{canonical_hash({'request_id': request.request_id, 'issued_at': issued_at})[7:19]}"

        permit = GovernedPermit(
            permit_id=permit_id,
            request_id=request.request_id,
            subject_id=request.subject_id,
            agent_id=request.agent_id,
            operator_ref=request.operator_ref,
            authority_chain_ref=request.authority_chain_ref,
            requested_action_type=request.requested_action_type,
            scope=request.scope,
            evidence_refs=request.evidence_refs,
            proof_bundle_refs=request.proof_bundle_refs,
            identity_ref=request.identity_ref,
            admission_ref=request.admission_ref,
            freshness_ref=request.freshness_ref,
            redaction_ref=request.redaction_ref,
            retention_ref=request.retention_ref,
            capability_ref=request.capability_ref,
            risk_class=request.risk_class,
            issued_at=issued_at,
            expires_at=expires_at,
            status="granted",
            deny_reasons=(),
            permit_kind=request.permit_kind,
        )
        self._store.put(permit)

        receipt = PermitReceipt(
            receipt_id=f"rcpt_{uuid.uuid4().hex[:12]}",
            permit_id=permit.permit_id,
            request_id=request.request_id,
            status="granted",
            issued_at=issued_at,
            permit_hash=permit.permit_hash,
        )
        self._mint_log.append(
            {
                "event": "gpp.permit.granted",
                "permit_id": permit.permit_id,
                "request_id": request.request_id,
                "permit_hash": permit.permit_hash,
                "receipt_hash": receipt.receipt_hash,
            }
        )
        return PermitDecision(status="granted", permit=permit, receipt=receipt)

    def revoke(self, revocation: PermitRevocation) -> bool:
        return self._store.revoke(revocation)

    def _deny(
        self,
        request: PermitRequest,
        reasons: list[PermitDenyReason],
        *,
        now: str,
    ) -> PermitDecision:
        permit_id = f"gpp_denied_{canonical_hash(request.request_id)[7:15]}"
        permit = GovernedPermit(
            permit_id=permit_id,
            request_id=request.request_id,
            subject_id=request.subject_id,
            agent_id=request.agent_id,
            operator_ref=request.operator_ref,
            authority_chain_ref=request.authority_chain_ref,
            requested_action_type=request.requested_action_type,
            scope=request.scope,
            evidence_refs=request.evidence_refs,
            proof_bundle_refs=request.proof_bundle_refs,
            identity_ref=request.identity_ref,
            admission_ref=request.admission_ref,
            freshness_ref=request.freshness_ref,
            redaction_ref=request.redaction_ref,
            retention_ref=request.retention_ref,
            capability_ref=request.capability_ref,
            risk_class=request.risk_class,
            issued_at=now,
            expires_at=now,
            status="denied",
            deny_reasons=tuple(reasons),
            permit_kind=request.permit_kind,
        )
        receipt = PermitReceipt(
            receipt_id=f"rcpt_{uuid.uuid4().hex[:12]}",
            permit_id=permit.permit_id,
            request_id=request.request_id,
            status="denied",
            issued_at=now,
            permit_hash=permit.permit_hash,
        )
        self._mint_log.append(
            {
                "event": "gpp.permit.denied",
                "permit_id": permit.permit_id,
                "request_id": request.request_id,
                "deny_reasons": [r.code for r in reasons],
            }
        )
        return PermitDecision(status="denied", permit=permit, deny_reasons=tuple(reasons), receipt=receipt)


__all__ = ["PermitAuthority", "_GPP_ISSUER"]
