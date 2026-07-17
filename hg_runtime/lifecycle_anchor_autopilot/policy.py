"""Lifecycle anchor autopilot policy."""

from __future__ import annotations

from hg_runtime.external_witness_journal.schema import WitnessEventClass, WitnessImportanceClass
from hg_runtime.lifecycle_anchor_autopilot.push_resolver import resolve_lifecycle_push_policy
from hg_runtime.lifecycle_anchor_autopilot.schema import (
    AnchorAutopilotDecision,
    AnchorAutopilotMode,
    LifecycleAnchorEvent,
    LifecycleAnchorPolicy,
)

AUTO_LIFECYCLE_EVENTS = {e.value for e in LifecycleAnchorEvent}


def load_policy() -> LifecycleAnchorPolicy:
    push = resolve_lifecycle_push_policy()
    return LifecycleAnchorPolicy(
        lifecycle_local_append_enabled=True,
        lifecycle_autopush_enabled=push.lifecycle_autopush_enabled,
    )


def decide_lifecycle_autopilot(
    event: LifecycleAnchorEvent,
    *,
    policy: LifecycleAnchorPolicy | None = None,
    agent_requested: bool = False,
    operator_invoked: bool = False,
    push_requested: bool = False,
    importance: WitnessImportanceClass | None = None,
    witness_event: WitnessEventClass | None = None,
) -> AnchorAutopilotDecision:
    policy = policy or load_policy()
    witness_event = witness_event or WitnessEventClass(event.value) if event.value in AUTO_LIFECYCLE_EVENTS else None

    if agent_requested and push_requested and not operator_invoked:
        return AnchorAutopilotDecision(
            mode=AnchorAutopilotMode.DENY,
            verdict="RED_AGENT_DIRECT_ANCHOR_PUSH",
            reason="agent cannot live-push anchors directly",
        )

    if importance == WitnessImportanceClass.IMPORTANT and policy.important_marker_queues_by_default and agent_requested:
        return AnchorAutopilotDecision(
            mode=AnchorAutopilotMode.QUEUE_FOR_OPERATOR,
            verdict="YELLOW_LIVE_PUSH_DISABLED_BY_POLICY",
            reason="important marker queued for operator",
            queued=True,
        )

    if importance in {WitnessImportanceClass.INCIDENT, WitnessImportanceClass.RELEASE}:
        return AnchorAutopilotDecision(
            mode=AnchorAutopilotMode.QUEUE_FOR_OPERATOR,
            verdict="YELLOW_LIVE_PUSH_DISABLED_BY_POLICY",
            reason=f"{importance.value} queued for operator",
            queued=True,
        )

    if event in LifecycleAnchorEvent and policy.lifecycle_local_append_enabled:
        if (
            push_requested
            and operator_invoked
            and policy.lifecycle_autopush_enabled
        ):
            return AnchorAutopilotDecision(
                mode=AnchorAutopilotMode.LIVE_PUSH,
                verdict="GREEN_LIFECYCLE_ANCHOR_AUTOPILOT_READY",
                reason="lifecycle autopush policy satisfied",
                push_allowed=True,
            )
        return AnchorAutopilotDecision(
            mode=AnchorAutopilotMode.LOCAL_ONLY,
            verdict="GREEN_LIFECYCLE_ANCHOR_AUTOPILOT_READY",
            reason="lifecycle local append",
        )

    return AnchorAutopilotDecision(
        mode=AnchorAutopilotMode.QUEUE_FOR_OPERATOR,
        verdict="YELLOW_LIVE_PUSH_DISABLED_BY_POLICY",
        reason="non-lifecycle event queued",
        queued=True,
    )
