"""Bridge to Phase 17 external action candidate creation."""

from __future__ import annotations

from hg_runtime.capability_broker.schema import new_decision_id
from hg_runtime.external_write_authority.broker_integration import broker_may_create_candidate, create_candidate_from_broker_admission
from hg_runtime.governed_work_loop.action_quota import ExternalActionQuota


def create_external_candidate(
    *,
    run_id: str,
    platform: str,
    action_type: str,
    content: str,
    scope: str,
    quota: ExternalActionQuota,
) -> tuple[str | None, str | None]:
    if not broker_may_create_candidate("create_external_action_candidate"):
        return None, "RED_CAPABILITY_BROKER_BYPASSED"
    if not quota.may_create_candidate():
        return None, "quota_exceeded"
    broker_ref = f"broker:create_external_action_candidate:{new_decision_id()}"
    cand = create_candidate_from_broker_admission(
        run_id=run_id,
        platform=platform,
        action_type=action_type,
        content=content,
        scope=scope,
        capability_decision_ref=broker_ref,
    )
    quota.record_candidate()
    return cand.candidate_id, broker_ref
