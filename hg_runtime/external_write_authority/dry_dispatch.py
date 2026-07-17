"""Dry dispatch — receipts only, no live platform calls."""

from __future__ import annotations

from hg_runtime.external_write_authority.action_candidate import load_candidate, update_candidate_status
from hg_runtime.external_write_authority.errors import ExternalWriteLiveDispatchForbidden
from hg_runtime.external_write_authority.permit import load_permit
from hg_runtime.external_write_authority.receipts import (
    ExternalWriteDryDispatchPlan,
    ExternalWriteDryDispatchReceipt,
    write_dry_dispatch_receipt,
    write_refusal_receipt,
)
from hg_runtime.external_write_authority.schema import (
    CandidateStatus,
    PermitDenyReason,
    load_policy,
    new_id,
    now_iso,
)

# Endpoint map for dry-run labeling only — never called in Phase 17.
_WOULD_CALL_ENDPOINTS = {
    ("moltbook", "publish_post"): "POST /api/v1/posts (DRY-RUN — NOT CALLED)",
    ("fourclaw", "publish_post"): "POST /api/posts (DRY-RUN — NOT CALLED)",
    ("moltbook", "reply"): "POST /api/v1/replies (DRY-RUN — NOT CALLED)",
    ("fourclaw", "comment"): "POST /api/comments (DRY-RUN — NOT CALLED)",
}


def _would_call_endpoint(platform: str, action_type: str) -> str | None:
    return _WOULD_CALL_ENDPOINTS.get((platform.lower(), action_type))


def execute_dry_dispatch(*, run_id: str, permit_id: str) -> ExternalWriteDryDispatchReceipt | None:
    policy = load_policy()
    if policy.get("live_writes_allowed"):
        raise ExternalWriteLiveDispatchForbidden("live writes forbidden in Phase 17")

    permit = load_permit(run_id, permit_id)
    if not permit:
        write_refusal_receipt(
            run_id=run_id,
            deny_reasons=[PermitDenyReason.MISSING_PERMIT],
        )
        return None

    if permit.is_revoked():
        write_refusal_receipt(
            run_id=run_id,
            deny_reasons=[PermitDenyReason.REVOKED_PERMIT],
            candidate_ref=permit.candidate_ref,
        )
        return None

    if permit.is_expired():
        write_refusal_receipt(
            run_id=run_id,
            deny_reasons=[PermitDenyReason.EXPIRED_PERMIT],
            candidate_ref=permit.candidate_ref,
        )
        return None

    if permit.live_dispatch_allowed:
        raise ExternalWriteLiveDispatchForbidden("live_dispatch_allowed must be false in Phase 17")

    cand = load_candidate(run_id, permit.candidate_ref)
    if not cand:
        write_refusal_receipt(
            run_id=run_id,
            deny_reasons=[PermitDenyReason.MISSING_CANDIDATE],
            candidate_ref=permit.candidate_ref,
        )
        return None

    plan = ExternalWriteDryDispatchPlan(
        dispatch_plan_id=new_id("ext-dry-plan"),
        permit_ref=permit_id,
        candidate_ref=permit.candidate_ref,
        platform=permit.requested_platform,
        action_type=permit.permitted_action_type.value,
        scope=permit.permitted_scope,
        content_hash=cand.content_hash,
        dry_run_only=True,
        live_dispatch_allowed=False,
        created_at=now_iso(),
    ).with_hash()

    endpoint = _would_call_endpoint(permit.requested_platform, permit.permitted_action_type.value)
    receipt = write_dry_dispatch_receipt(
        run_id=run_id,
        plan=plan,
        would_call_endpoint=endpoint,
    )
    update_candidate_status(run_id, permit.candidate_ref, CandidateStatus.DRY_RUN_COMPLETED)
    return receipt
