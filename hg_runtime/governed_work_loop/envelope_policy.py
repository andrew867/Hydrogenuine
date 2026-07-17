"""Envelope policy enforcement."""

from __future__ import annotations

from hg_runtime.governed_work_loop.schema import BLOCKED_WORK_TYPES, GovernedWorkLoopVerdict, load_governed_work_policy
from hg_runtime.governed_work_loop.work_envelope import ExternalActionEnvelope, GovernedWorkEnvelope
from hg_runtime.governed_work_loop.work_item import GovernedWorkItem


def evaluate_work_item(
    envelope: GovernedWorkEnvelope,
    item: GovernedWorkItem,
    *,
    model_suggested: bool = False,
    review_queue_ref: str | None = None,
) -> tuple[bool, str | None]:
    policy = load_governed_work_policy()
    if item.work_type in BLOCKED_WORK_TYPES:
        return False, GovernedWorkLoopVerdict.RED_UNSCOPED_LIVE.value
    if not envelope.scope_allowed(item.scope_ref):
        return False, "out_of_envelope_scope"
    if not envelope.work_type_allowed(item.work_type):
        return False, "work_type_not_allowed"
    if item.requires_live_dispatch and not policy.get("zero_may_live_dispatch_by_default", False):
        return False, GovernedWorkLoopVerdict.YELLOW_LIVE_BLOCKED_BY_POLICY.value
    if model_suggested and policy.get("model_output_is_permission", False) is False:
        return False, "model_output_not_permission"
    if review_queue_ref and policy.get("review_queue_is_approval", False):
        return False, "review_queue_not_approval"
    if item.work_type == "mass_message" and not policy.get("mass_messaging_allowed", False):
        return False, GovernedWorkLoopVerdict.RED_UNSCOPED_LIVE.value
    return True, None


def zero_may_expand_envelope() -> bool:
    return bool(load_governed_work_policy().get("zero_may_expand_work_envelope", False))


def evaluate_live_dispatch(
    ext_envelope: ExternalActionEnvelope | None,
    *,
    phase18_live_permit_ref: str | None = None,
    platform_proof_ref: str | None = None,
    operator_prearm: bool = False,
) -> tuple[bool, str]:
    policy = load_governed_work_policy()
    if not policy.get("zero_may_live_dispatch_by_default", False):
        if not ext_envelope or not ext_envelope.live_dispatch_allowed:
            return False, GovernedWorkLoopVerdict.YELLOW_LIVE_ENVELOPE_NOT_ARMED.value
    if ext_envelope and ext_envelope.requires_operator_prearm and not operator_prearm:
        return False, GovernedWorkLoopVerdict.YELLOW_LIVE_ENVELOPE_NOT_ARMED.value
    if ext_envelope and ext_envelope.requires_phase18_live_permit and not phase18_live_permit_ref:
        return False, "RED_LIVE_ACTION_WITHOUT_PHASE18_LIVE_PERMIT"
    if ext_envelope and ext_envelope.requires_platform_proof and not platform_proof_ref:
        return False, "RED_LIVE_ACTION_WITHOUT_PLATFORM_PROOF"
    return False, GovernedWorkLoopVerdict.YELLOW_LIVE_BLOCKED_BY_POLICY.value
