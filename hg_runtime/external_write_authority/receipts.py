"""Dry dispatch and refusal receipts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.external_write_authority.schema import (
    ExternalWriteAuthorityVerdict,
    PermitDenyReason,
    STORE_ROOT,
    new_id,
    now_iso,
)


@dataclass
class ExternalWriteDryDispatchPlan:
    dispatch_plan_id: str
    permit_ref: str
    candidate_ref: str
    platform: str
    action_type: str
    scope: str
    content_hash: str
    dry_run_only: bool
    live_dispatch_allowed: bool
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "dispatch_plan_id": self.dispatch_plan_id,
            "permit_ref": self.permit_ref,
            "candidate_ref": self.candidate_ref,
            "platform": self.platform,
            "action_type": self.action_type,
            "scope": self.scope,
            "content_hash": self.content_hash,
            "dry_run_only": self.dry_run_only,
            "live_dispatch_allowed": self.live_dispatch_allowed,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ExternalWriteDryDispatchPlan:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        from hg_core.policy_safety.hashing import compute_record_hash

        return ExternalWriteDryDispatchPlan(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class ExternalWriteDryDispatchReceipt:
    dry_dispatch_receipt_id: str
    dispatch_plan_ref: str
    permit_ref: str
    candidate_ref: str
    platform: str
    action_type: str
    external_side_effect: bool
    created_at: str
    verdict: str
    would_call_endpoint: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "dry_dispatch_receipt_id": self.dry_dispatch_receipt_id,
            "dispatch_plan_ref": self.dispatch_plan_ref,
            "permit_ref": self.permit_ref,
            "candidate_ref": self.candidate_ref,
            "platform": self.platform,
            "action_type": self.action_type,
            "would_call_endpoint": self.would_call_endpoint,
            "external_side_effect": self.external_side_effect,
            "created_at": self.created_at,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> ExternalWriteDryDispatchReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        from hg_core.policy_safety.hashing import compute_record_hash

        return ExternalWriteDryDispatchReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class ExternalWriteRefusalReceipt:
    refusal_receipt_id: str
    deny_reasons: tuple[str, ...]
    created_at: str
    verdict: str
    candidate_ref: str | None = None
    authority_request_ref: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "refusal_receipt_id": self.refusal_receipt_id,
            "candidate_ref": self.candidate_ref,
            "authority_request_ref": self.authority_request_ref,
            "deny_reasons": list(self.deny_reasons),
            "created_at": self.created_at,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> ExternalWriteRefusalReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        from hg_core.policy_safety.hashing import compute_record_hash

        return ExternalWriteRefusalReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


def _receipts_dir(run_id: str) -> Path:
    return STORE_ROOT / run_id / "receipts"


def write_refusal_receipt(
    *,
    run_id: str,
    deny_reasons: list[PermitDenyReason | str],
    candidate_ref: str | None = None,
    authority_request_ref: str | None = None,
) -> ExternalWriteRefusalReceipt:
    reasons = tuple(r.value if isinstance(r, PermitDenyReason) else r for r in deny_reasons)
    receipt = ExternalWriteRefusalReceipt(
        refusal_receipt_id=new_id("ext-refusal"),
        candidate_ref=candidate_ref,
        authority_request_ref=authority_request_ref,
        deny_reasons=reasons,
        created_at=now_iso(),
        verdict=ExternalWriteAuthorityVerdict.RED_MISSING_PERMIT.value
        if PermitDenyReason.MISSING_PERMIT.value in reasons
        else "REFUSED",
    ).with_hash()
    path = _receipts_dir(run_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{receipt.refusal_receipt_id}.json").write_text(
        json.dumps(receipt.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def write_dry_dispatch_receipt(
    *,
    run_id: str,
    plan: ExternalWriteDryDispatchPlan,
    would_call_endpoint: str | None,
) -> ExternalWriteDryDispatchReceipt:
    receipt = ExternalWriteDryDispatchReceipt(
        dry_dispatch_receipt_id=new_id("ext-dry-rcpt"),
        dispatch_plan_ref=plan.dispatch_plan_id,
        permit_ref=plan.permit_ref,
        candidate_ref=plan.candidate_ref,
        platform=plan.platform,
        action_type=plan.action_type,
        would_call_endpoint=would_call_endpoint,
        external_side_effect=False,
        created_at=now_iso(),
        verdict=ExternalWriteAuthorityVerdict.YELLOW_EXTERNAL_WRITE_DRY_RUN_ONLY.value,
    ).with_hash()
    path = _receipts_dir(run_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{receipt.dry_dispatch_receipt_id}.json").write_text(
        json.dumps(receipt.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return receipt
