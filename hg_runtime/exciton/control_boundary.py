"""EXCITON Phase 0 control boundary — routes requests, never grants authority.

Every control resolves to exactly one ``ExcitonControlDecisionKind``. Allowed controls map
to read-only / draft / queue / full-stop. Everything else — including any unknown control —
is ``DENY`` (default-deny). No decision ever returns permission or authority; the frozen
constants on every decision payload are structurally ``permission_granted=False`` and
``authority_created=False``.
"""

from __future__ import annotations

from hg_runtime.exciton.schema import (
    ExcitonControlDecision,
    ExcitonControlDecisionKind,
    ExcitonControlKind,
    ExcitonControlRequest,
)

D = ExcitonControlDecisionKind

# The only controls EXCITON Phase 0 permits, and the decision each resolves to.
ALLOWED_DECISIONS: dict[ExcitonControlKind, ExcitonControlDecisionKind] = {
    ExcitonControlKind.REFRESH_STATUS: D.ALLOW_READ_ONLY,
    ExcitonControlKind.OPEN_PROOF_LINK: D.ALLOW_READ_ONLY,
    ExcitonControlKind.COPY_SAFE_SUMMARY: D.ALLOW_READ_ONLY,
    ExcitonControlKind.REQUEST_SELF_MIRROR_QUERY: D.ALLOW_READ_ONLY,
    ExcitonControlKind.REQUEST_PROOF_RECHECK: D.ALLOW_READ_ONLY,
    ExcitonControlKind.RUN_DRY_RUN_GATE: D.ALLOW_READ_ONLY,
    ExcitonControlKind.ADD_OPERATOR_NOTE: D.ALLOW_DRAFT_ONLY,
    ExcitonControlKind.REQUEST_ANCHOR_QUEUE_REVIEW: D.QUEUE_FOR_OPERATOR,
    ExcitonControlKind.STOP_AGENT: D.FULL_STOP,
    ExcitonControlKind.PANIC_STOP: D.FULL_STOP,
    # Phase 1 social/soak — read, draft, queue; never direct publish
    ExcitonControlKind.REFRESH_SOCIAL_STATUS: D.ALLOW_READ_ONLY,
    ExcitonControlKind.RUN_SOCIAL_READ_FIXTURE: D.ALLOW_READ_ONLY,
    ExcitonControlKind.RUN_SOCIAL_READ_LIVE: D.ALLOW_READ_ONLY,
    ExcitonControlKind.GENERATE_SOCIAL_DRAFT: D.ALLOW_DRAFT_ONLY,
    ExcitonControlKind.QUEUE_SOCIAL_DRAFT: D.QUEUE_FOR_OPERATOR,
    ExcitonControlKind.APPROVE_SOCIAL_PUBLISH: D.QUEUE_FOR_OPERATOR,
    ExcitonControlKind.DENY_SOCIAL_DRAFT: D.ALLOW_READ_ONLY,
    ExcitonControlKind.STOP_SOAK: D.FULL_STOP,
    ExcitonControlKind.CONFIRM_PUBLISH_AFTER_OBSERVATION: D.QUEUE_FOR_OPERATOR,
    ExcitonControlKind.APPROVE_QUEUE_ITEM: D.QUEUE_FOR_OPERATOR,
    ExcitonControlKind.DENY_QUEUE_ITEM: D.QUEUE_FOR_OPERATOR,
    ExcitonControlKind.ENABLE_PUBLISH_APPROVED_ONLY: D.QUEUE_FOR_OPERATOR,
}

# Explicitly forbidden controls — always DENY. Listed for clarity and the gate; the
# default-deny below would catch them regardless.
FORBIDDEN_CONTROLS: frozenset[ExcitonControlKind] = frozenset(
    {
        ExcitonControlKind.PUBLISH_SOCIAL,
        ExcitonControlKind.DIRECT_PUBLISH,
        ExcitonControlKind.APPROVE_ALL,
        ExcitonControlKind.SEND_EMAIL,
        ExcitonControlKind.CREATE_ACCOUNT,
        ExcitonControlKind.LOGIN_FORM_SUBMIT,
        ExcitonControlKind.MUTATE_MEMORY,
        ExcitonControlKind.MUTATE_SOURCE,
        ExcitonControlKind.PUSH_GITHUB_ANCHOR,
        ExcitonControlKind.DELETE_PROOF_BUNDLE,
        ExcitonControlKind.START_OEA,
        ExcitonControlKind.START_TER,
        ExcitonControlKind.APPLY_SRP,
        ExcitonControlKind.ENABLE_LIVE_MIC,
        ExcitonControlKind.ENABLE_PLAYBACK,
        ExcitonControlKind.START_SOAK,
        ExcitonControlKind.START_AUTONOMOUS_LOOP,
    }
)

_REASON = {
    D.ALLOW_READ_ONLY: "safe read-only action; no external side effect",
    D.ALLOW_DRAFT_ONLY: "draft/note only; not an instruction or consent",
    D.QUEUE_FOR_OPERATOR: "queued for human disposition; EXCITON does not approve or execute",
    D.FULL_STOP: "stop/panic; always available and non-blockable",
    D.DENY: "forbidden in EXCITON Phase 0; routed to deny, never executed",
}


class ExcitonControlBoundary:
    """Decides every control request. Default-deny. Never grants authority."""

    def decide(self, request: ExcitonControlRequest) -> ExcitonControlDecision:
        kind = ALLOWED_DECISIONS.get(request.control, D.DENY)
        return ExcitonControlDecision(
            request_id=request.request_id,
            control=request.control,
            decision=kind,
            reason=_REASON[kind],
        )

    @staticmethod
    def is_forbidden(control: ExcitonControlKind) -> bool:
        return control in FORBIDDEN_CONTROLS or control not in ALLOWED_DECISIONS


__all__ = [
    "ALLOWED_DECISIONS",
    "FORBIDDEN_CONTROLS",
    "ExcitonControlBoundary",
]
