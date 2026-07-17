"""Lifecycle anchor autopilot schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hg_runtime.external_witness_journal.schema import WitnessEventClass, WitnessImportanceClass

FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


class AnchorAutopilotMode(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    LIVE_PUSH = "LIVE_PUSH"
    QUEUE_FOR_OPERATOR = "QUEUE_FOR_OPERATOR"
    DENY = "DENY"


class LifecycleAnchorEvent(str, Enum):
    BOOT_START = "BOOT_START"
    BOOT_VERIFIED = "BOOT_VERIFIED"
    WRR_START = "WAKE_REFRESH_START"
    WRR_COMPLETE = "WAKE_REFRESH_COMPLETE"
    FIRST_WAKE_START = "FIRST_WAKE_START"
    FIRST_WAKE_COMPLETE = "FIRST_WAKE_COMPLETE"
    WEATHER_VOICE_START = "WEATHER_VOICE_START"
    WEATHER_VOICE_COMPLETE = "WEATHER_VOICE_COMPLETE"
    SLEEP_START = "SLEEP_START"
    SLEEP_COMPLETE = "SLEEP_COMPLETE"
    CLEAN_STOP = "CLEAN_STOP"
    PANIC_ENTERED = "PANIC_ENTERED"
    PANIC_CLEARED = "PANIC_CLEARED"


LIFECYCLE_TO_WITNESS: dict[LifecycleAnchorEvent, WitnessEventClass] = {
    LifecycleAnchorEvent.BOOT_START: WitnessEventClass.BOOT_START,
    LifecycleAnchorEvent.BOOT_VERIFIED: WitnessEventClass.BOOT_VERIFIED,
    LifecycleAnchorEvent.WRR_START: WitnessEventClass.WAKE_REFRESH_START,
    LifecycleAnchorEvent.WRR_COMPLETE: WitnessEventClass.WAKE_REFRESH_COMPLETE,
    LifecycleAnchorEvent.FIRST_WAKE_START: WitnessEventClass.FIRST_WAKE_START,
    LifecycleAnchorEvent.FIRST_WAKE_COMPLETE: WitnessEventClass.FIRST_WAKE_COMPLETE,
    LifecycleAnchorEvent.WEATHER_VOICE_START: WitnessEventClass.WEATHER_VOICE_START,
    LifecycleAnchorEvent.WEATHER_VOICE_COMPLETE: WitnessEventClass.WEATHER_VOICE_COMPLETE,
    LifecycleAnchorEvent.SLEEP_START: WitnessEventClass.SLEEP_START,
    LifecycleAnchorEvent.SLEEP_COMPLETE: WitnessEventClass.SLEEP_COMPLETE,
    LifecycleAnchorEvent.CLEAN_STOP: WitnessEventClass.CLEAN_STOP,
    LifecycleAnchorEvent.PANIC_ENTERED: WitnessEventClass.PANIC_ENTERED,
    LifecycleAnchorEvent.PANIC_CLEARED: WitnessEventClass.PANIC_CLEARED,
}


@dataclass
class LifecycleAnchorPolicy:
    lifecycle_local_append_enabled: bool = True
    lifecycle_autopush_enabled: bool = False
    agent_direct_push_forbidden: bool = True
    important_marker_queues_by_default: bool = True
    incident_marker_queues_by_default: bool = True
    release_marker_queues_by_default: bool = True
    sanitize_payloads: bool = True
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "lifecycle-anchor-policy",
            **{k: getattr(self, k) for k in self.__dataclass_fields__ if k not in FROZEN_FALSE},
            **FROZEN_FALSE,
        }


@dataclass
class AnchorAutopilotDecision:
    mode: AnchorAutopilotMode
    verdict: str
    reason: str
    push_allowed: bool = False
    queued: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "anchor-autopilot-decision",
            "mode": self.mode.value,
            "verdict": self.verdict,
            "reason": self.reason,
            "push_allowed": self.push_allowed,
            "queued": self.queued,
            **FROZEN_FALSE,
        }


@dataclass
class AnchorAutopilotQueueItem:
    item_id: str
    event_class: str
    summary: str
    facts: dict[str, Any] = field(default_factory=dict)
    queued_reason: str = ""
    agent_requested: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "anchor-autopilot-queue-item",
            "item_id": self.item_id,
            "event_class": self.event_class,
            "summary": self.summary,
            "facts": self.facts,
            "queued_reason": self.queued_reason,
            "agent_requested": self.agent_requested,
            **FROZEN_FALSE,
        }


@dataclass
class AnchorAutopilotReceipt:
    receipt_id: str
    event_class: str
    decision: AnchorAutopilotDecision
    local_committed: bool = False
    pushed: bool = False
    queue_item_id: str | None = None
    journal_receipt_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "anchor-autopilot-receipt",
            "receipt_id": self.receipt_id,
            "event_class": self.event_class,
            "decision": self.decision.to_payload(),
            "local_committed": self.local_committed,
            "pushed": self.pushed,
            "queue_item_id": self.queue_item_id,
            "journal_receipt_id": self.journal_receipt_id,
            **FROZEN_FALSE,
        }
