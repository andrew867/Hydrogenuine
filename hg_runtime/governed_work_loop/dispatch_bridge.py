"""Bridge to Phase 17/18/19 dispatch paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.external_write_authority.authority_request import create_authority_request
from hg_runtime.external_write_authority.dry_dispatch import execute_dry_dispatch
from hg_runtime.external_write_authority.operator_confirmation import create_dry_operator_confirmation
from hg_runtime.external_write_authority.permit import issue_permit
from hg_runtime.governed_work_loop.envelope_policy import evaluate_live_dispatch
from hg_runtime.governed_work_loop.schema import GovernedWorkLoopVerdict, new_id, now_iso
from hg_runtime.governed_work_loop.work_envelope import ExternalActionEnvelope


@dataclass
class GovernedDispatchDecision:
    governed_dispatch_decision_id: str
    verdict: str
    external_side_effect: bool
    dry_dispatch_ref: str | None
    live_dispatch_ref: str | None
    refusal_reasons: tuple[str, ...]
    created_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "governed_dispatch_decision_id": self.governed_dispatch_decision_id,
            "verdict": self.verdict,
            "external_side_effect": self.external_side_effect,
            "dry_dispatch_ref": self.dry_dispatch_ref,
            "live_dispatch_ref": self.live_dispatch_ref,
            "refusal_reasons": list(self.refusal_reasons),
            "created_at": self.created_at,
        }


def request_authority_for_candidate(
    *,
    run_id: str,
    candidate_id: str,
    broker_ref: str,
) -> str:
    req = create_authority_request(
        run_id=run_id,
        candidate_id=candidate_id,
        capability_decision_ref=broker_ref,
    )
    return req.authority_request_id


def execute_governed_dry_dispatch(
    *,
    run_id: str,
    candidate_id: str,
    authority_request_id: str,
    platform: str,
    action_type: str,
    scope: str,
    content_hash: str,
) -> GovernedDispatchDecision:
    conf = create_dry_operator_confirmation(
        run_id=run_id,
        operator_ref="governed-work-loop",
        candidate_id=candidate_id,
        authority_request_id=authority_request_id,
        phrase=f"dry-run authorize candidate {candidate_id}",
        platform=platform,
        action_type=action_type,
        scope=scope,
        content_hash=content_hash,
    )
    decision = issue_permit(
        run_id=run_id,
        authority_request_id=authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    if not decision.granted or not decision.permit:
        return GovernedDispatchDecision(
            governed_dispatch_decision_id=new_id("gov-dispatch"),
            verdict="GREEN_WORK_REFUSED",
            external_side_effect=False,
            dry_dispatch_ref=None,
            live_dispatch_ref=None,
            refusal_reasons=tuple(r.value if hasattr(r, "value") else str(r) for r in decision.deny_reasons),
            created_at=now_iso(),
        )
    receipt = execute_dry_dispatch(run_id=run_id, permit_id=decision.permit.permit_id)
    dry_ref = receipt.dry_dispatch_receipt_id if receipt else None
    return GovernedDispatchDecision(
        governed_dispatch_decision_id=new_id("gov-dispatch"),
        verdict="GREEN_WORK_COMPLETE" if receipt else "GREEN_WORK_REFUSED",
        external_side_effect=False,
        dry_dispatch_ref=dry_ref,
        live_dispatch_ref=None,
        refusal_reasons=() if receipt else ("dry_dispatch_failed",),
        created_at=now_iso(),
    )


def attempt_live_dispatch(
    ext_envelope: ExternalActionEnvelope | None,
    *,
    phase18_live_permit_ref: str | None = None,
    platform_proof_ref: str | None = None,
    operator_prearm: bool = False,
) -> GovernedDispatchDecision:
    allowed, reason = evaluate_live_dispatch(
        ext_envelope,
        phase18_live_permit_ref=phase18_live_permit_ref,
        platform_proof_ref=platform_proof_ref,
        operator_prearm=operator_prearm,
    )
    return GovernedDispatchDecision(
        governed_dispatch_decision_id=new_id("gov-dispatch"),
        verdict=reason if not allowed else GovernedWorkLoopVerdict.YELLOW_LIVE_BLOCKED_BY_POLICY.value,
        external_side_effect=False,
        dry_dispatch_ref=None,
        live_dispatch_ref=None,
        refusal_reasons=(reason,),
        created_at=now_iso(),
    )
