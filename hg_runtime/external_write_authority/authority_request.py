"""External write authority request."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from hg_runtime.external_write_authority.action_candidate import load_candidate
from hg_runtime.external_write_authority.schema import (
    ExternalActionType,
    STORE_ROOT,
    load_policy,
    new_id,
    now_iso,
)


@dataclass
class ExternalWriteAuthorityRequest:
    authority_request_id: str
    candidate_ref: str
    requested_platform: str
    requested_action_type: ExternalActionType
    requested_scope: str
    risk_class: str
    capability_decision_ref: str
    created_at: str
    expires_at: str
    operator_ref: str | None = None
    review_decision_ref: str | None = None
    provider_receipt_ref: str | None = None
    live_read_receipt_refs: tuple[str, ...] = ()
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "authority_request_id": self.authority_request_id,
            "candidate_ref": self.candidate_ref,
            "operator_ref": self.operator_ref,
            "review_decision_ref": self.review_decision_ref,
            "provider_receipt_ref": self.provider_receipt_ref,
            "live_read_receipt_refs": list(self.live_read_receipt_refs),
            "capability_decision_ref": self.capability_decision_ref,
            "requested_platform": self.requested_platform,
            "requested_action_type": self.requested_action_type.value,
            "requested_scope": self.requested_scope,
            "risk_class": self.risk_class,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ExternalWriteAuthorityRequest:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        from hg_core.policy_safety.hashing import compute_record_hash

        return ExternalWriteAuthorityRequest(**{**self.__dict__, "hash": compute_record_hash(body)})


def _store(run_id: str) -> Path:
    return STORE_ROOT / run_id / "authority_requests"


def create_authority_request(
    *,
    run_id: str,
    candidate_id: str,
    capability_decision_ref: str,
    review_decision_ref: str | None = None,
) -> ExternalWriteAuthorityRequest:
    cand = load_candidate(run_id, candidate_id)
    if not cand:
        raise ValueError("candidate required")
    policy = load_policy()
    ttl = int(policy.get("authority_request_ttl_seconds", 1800))
    created = now_iso()
    exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    req = ExternalWriteAuthorityRequest(
        authority_request_id=new_id("ext-auth-req"),
        candidate_ref=candidate_id,
        capability_decision_ref=capability_decision_ref,
        review_decision_ref=review_decision_ref,
        provider_receipt_ref=cand.provider_receipt_ref,
        live_read_receipt_refs=cand.live_read_receipt_refs,
        requested_platform=cand.requested_platform,
        requested_action_type=cand.requested_action_type,
        requested_scope=cand.scope,
        risk_class=cand.risk_class,
        created_at=created,
        expires_at=exp,
    ).with_hash()
    path = _store(run_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{req.authority_request_id}.json").write_text(
        json.dumps(req.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    from hg_runtime.external_write_authority.action_candidate import update_candidate_status
    from hg_runtime.external_write_authority.schema import CandidateStatus

    update_candidate_status(run_id, candidate_id, CandidateStatus.AWAITING_AUTHORITY)
    return req


def load_authority_request(run_id: str, request_id: str) -> ExternalWriteAuthorityRequest | None:
    path = _store(run_id) / f"{request_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExternalWriteAuthorityRequest(
        authority_request_id=data["authority_request_id"],
        candidate_ref=data["candidate_ref"],
        operator_ref=data.get("operator_ref"),
        review_decision_ref=data.get("review_decision_ref"),
        provider_receipt_ref=data.get("provider_receipt_ref"),
        live_read_receipt_refs=tuple(data.get("live_read_receipt_refs") or ()),
        capability_decision_ref=data["capability_decision_ref"],
        requested_platform=data["requested_platform"],
        requested_action_type=ExternalActionType(data["requested_action_type"]),
        requested_scope=data["requested_scope"],
        risk_class=data["risk_class"],
        created_at=data["created_at"],
        expires_at=data["expires_at"],
        hash=data.get("hash"),
    )
