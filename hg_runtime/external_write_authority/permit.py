"""External write permit — dry-run only in Phase 17."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from hg_runtime.external_write_authority.action_candidate import load_candidate, update_candidate_status
from hg_runtime.external_write_authority.authority_request import load_authority_request
from hg_runtime.external_write_authority.operator_confirmation import (
    OperatorExternalWriteConfirmation,
    load_confirmation,
)
from hg_runtime.external_write_authority.receipts import write_refusal_receipt
from hg_runtime.external_write_authority.schema import (
    CandidateStatus,
    ExternalActionType,
    PermitDenyReason,
    PermitStatus,
    STORE_ROOT,
    load_policy,
    new_id,
    now_iso,
)
from hg_runtime.external_write_authority.scope_policy import (
    action_matches,
    platform_matches,
    scope_matches,
    validate_scope_no_expansion,
)


@dataclass
class ExternalWritePermit:
    permit_id: str
    authority_request_ref: str
    candidate_ref: str
    requested_platform: str
    permitted_action_type: ExternalActionType
    permitted_scope: str
    risk_class: str
    issued_at: str
    expires_at: str
    status: PermitStatus
    dry_run_only: bool
    live_dispatch_allowed: bool
    deny_reasons: tuple[str, ...] = ()
    operator_confirmation_ref: str | None = None
    revoked_at: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "permit_id": self.permit_id,
            "authority_request_ref": self.authority_request_ref,
            "candidate_ref": self.candidate_ref,
            "operator_confirmation_ref": self.operator_confirmation_ref,
            "requested_platform": self.requested_platform,
            "permitted_action_type": self.permitted_action_type.value,
            "permitted_scope": self.permitted_scope,
            "risk_class": self.risk_class,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "status": self.status.value,
            "deny_reasons": list(self.deny_reasons),
            "dry_run_only": self.dry_run_only,
            "live_dispatch_allowed": self.live_dispatch_allowed,
            "hash": self.hash,
        }

    def with_hash(self) -> ExternalWritePermit:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        from hg_core.policy_safety.hashing import compute_record_hash

        return ExternalWritePermit(**{**self.__dict__, "hash": compute_record_hash(body)})

    def is_expired(self, *, at: str | None = None) -> bool:
        ts = at or now_iso()
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            cur = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return cur >= exp
        except ValueError:
            return True

    def is_revoked(self) -> bool:
        return self.status == PermitStatus.REVOKED or self.revoked_at is not None


@dataclass
class ExternalWritePermitDecision:
    granted: bool
    permit: ExternalWritePermit | None = None
    deny_reasons: tuple[PermitDenyReason, ...] = ()


class ExternalWritePermitVerifier:
    """Verify permit preconditions — no self-mint from model output."""

    def verify_candidate(
        self,
        *,
        run_id: str,
        candidate_id: str,
    ) -> tuple[Any | None, list[PermitDenyReason]]:
        cand = load_candidate(run_id, candidate_id)
        if not cand:
            return None, [PermitDenyReason.MISSING_CANDIDATE]
        if cand.is_expired():
            return cand, [PermitDenyReason.EXPIRED_CANDIDATE]
        if cand.status in (CandidateStatus.EXPIRED, CandidateStatus.INVALID, CandidateStatus.REVOKED):
            return cand, [PermitDenyReason.STALE_CANDIDATE]
        return cand, []

    def verify_capability(
        self,
        *,
        capability_decision_ref: str | None,
        expected_action: str = "create_external_action_candidate",
    ) -> list[PermitDenyReason]:
        if not capability_decision_ref:
            return [PermitDenyReason.MISSING_CAPABILITY_DECISION]
        if capability_decision_ref.startswith("model_output:"):
            return [PermitDenyReason.MODEL_OUTPUT_NOT_AUTHORITY]
        if expected_action not in capability_decision_ref and "create_external_action_candidate" not in capability_decision_ref:
            return [PermitDenyReason.CAPABILITY_MISMATCH]
        return []

    def verify_confirmation(
        self,
        *,
        run_id: str,
        confirmation: OperatorExternalWriteConfirmation | None,
        candidate: Any,
    ) -> list[PermitDenyReason]:
        if not confirmation:
            return [PermitDenyReason.MISSING_OPERATOR_CONFIRMATION]
        if confirmation.is_expired():
            return [PermitDenyReason.STALE_CONFIRMATION]
        if confirmation.confirmed_content_hash != candidate.content_hash:
            return [PermitDenyReason.CONTENT_HASH_MISMATCH]
        if not platform_matches(confirmation.confirmed_platform, candidate.requested_platform):
            return [PermitDenyReason.PLATFORM_MISMATCH]
        if not action_matches(confirmation.confirmed_action_type, candidate.requested_action_type):
            return [PermitDenyReason.ACTION_MISMATCH]
        if not scope_matches(confirmation.confirmed_scope, candidate.scope):
            return [PermitDenyReason.SCOPE_EXPANSION]
        return []


def _store(run_id: str) -> Path:
    return STORE_ROOT / run_id / "permits"


def issue_permit(
    *,
    run_id: str,
    authority_request_id: str,
    operator_confirmation_id: str,
) -> ExternalWritePermitDecision:
    policy = load_policy()
    verifier = ExternalWritePermitVerifier()
    req = load_authority_request(run_id, authority_request_id)
    if not req:
        write_refusal_receipt(run_id=run_id, deny_reasons=[PermitDenyReason.MISSING_CANDIDATE])
        return ExternalWritePermitDecision(granted=False, deny_reasons=(PermitDenyReason.MISSING_CANDIDATE,))

    if req.review_decision_ref and policy.get("review_queue_is_approval") is False:
        # Review ref may exist but must not alone grant permit — confirmation still required.
        _ = req.review_decision_ref

    cand, cand_reasons = verifier.verify_candidate(run_id=run_id, candidate_id=req.candidate_ref)
    cap_reasons = verifier.verify_capability(capability_decision_ref=req.capability_decision_ref)
    conf = load_confirmation(run_id, operator_confirmation_id)
    conf_reasons = verifier.verify_confirmation(run_id=run_id, confirmation=conf, candidate=cand) if cand else []

    deny = [*cand_reasons, *cap_reasons, *conf_reasons]
    if deny:
        write_refusal_receipt(
            run_id=run_id,
            deny_reasons=deny,
            candidate_ref=req.candidate_ref,
            authority_request_ref=authority_request_id,
        )
        update_candidate_status(run_id, req.candidate_ref, CandidateStatus.AUTHORITY_DENIED)
        return ExternalWritePermitDecision(granted=False, deny_reasons=tuple(deny))

    assert cand is not None
    scope_reasons = validate_scope_no_expansion(
        candidate_scope=cand.scope,
        requested_scope=req.requested_scope,
        permitted_scope=cand.scope,
    )
    if scope_reasons:
        write_refusal_receipt(
            run_id=run_id,
            deny_reasons=scope_reasons,
            candidate_ref=req.candidate_ref,
            authority_request_ref=authority_request_id,
        )
        return ExternalWritePermitDecision(granted=False, deny_reasons=tuple(scope_reasons))

    ttl = int(policy.get("permit_ttl_seconds", 600))
    issued = now_iso()
    exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    permit = ExternalWritePermit(
        permit_id=new_id("ext-permit"),
        authority_request_ref=authority_request_id,
        candidate_ref=req.candidate_ref,
        operator_confirmation_ref=operator_confirmation_id,
        requested_platform=cand.requested_platform,
        permitted_action_type=cand.requested_action_type,
        permitted_scope=cand.scope,
        risk_class=cand.risk_class,
        issued_at=issued,
        expires_at=exp,
        status=PermitStatus.ISSUED,
        dry_run_only=bool(policy.get("dry_run_only", True)),
        live_dispatch_allowed=bool(policy.get("live_dispatch_allowed", False)),
    ).with_hash()

    path = _store(run_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{permit.permit_id}.json").write_text(
        json.dumps(permit.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    update_candidate_status(run_id, req.candidate_ref, CandidateStatus.DRY_RUN_PLANNED)
    return ExternalWritePermitDecision(granted=True, permit=permit)


def load_permit(run_id: str, permit_id: str) -> ExternalWritePermit | None:
    path = _store(run_id) / f"{permit_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExternalWritePermit(
        permit_id=data["permit_id"],
        authority_request_ref=data["authority_request_ref"],
        candidate_ref=data["candidate_ref"],
        operator_confirmation_ref=data.get("operator_confirmation_ref"),
        requested_platform=data["requested_platform"],
        permitted_action_type=ExternalActionType(data["permitted_action_type"]),
        permitted_scope=data["permitted_scope"],
        risk_class=data["risk_class"],
        issued_at=data["issued_at"],
        expires_at=data["expires_at"],
        revoked_at=data.get("revoked_at"),
        status=PermitStatus(data["status"]),
        deny_reasons=tuple(data.get("deny_reasons") or ()),
        dry_run_only=data.get("dry_run_only", True),
        live_dispatch_allowed=data.get("live_dispatch_allowed", False),
        hash=data.get("hash"),
    )


def revoke_permit(run_id: str, permit_id: str) -> ExternalWritePermit | None:
    permit = load_permit(run_id, permit_id)
    if not permit:
        return None
    revoked = ExternalWritePermit(
        **{
            **permit.__dict__,
            "status": PermitStatus.REVOKED,
            "revoked_at": now_iso(),
        }
    ).with_hash()
    path = _store(run_id) / f"{permit_id}.json"
    path.write_text(json.dumps(revoked.to_payload(), indent=2) + "\n", encoding="utf-8")
    update_candidate_status(run_id, permit.candidate_ref, CandidateStatus.REVOKED)
    return revoked


class ExternalWriteRevocation:
    @staticmethod
    def revoke(*, run_id: str, permit_id: str) -> ExternalWritePermit | None:
        return revoke_permit(run_id, permit_id)
