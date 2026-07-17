"""Append policy for witness journal events."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from hg_runtime.external_witness_journal.importance import is_lifecycle_event
from hg_runtime.external_witness_journal.schema import (
    AnchorWriterRequest,
    AnchorWriterRequestKind,
    WitnessAppendDecision,
    WitnessEventClass,
    WitnessImportanceClass,
    WitnessJournalConfig,
)

LOCAL_STATE = Path(".hg-local") / "external_witness_journal"
QUEUE_PATH = LOCAL_STATE / "operator_queue.json"
RATE_PATH = LOCAL_STATE / "rate_limit.json"


class AnchorSpamBlocked(Exception):
    code = "RED_EWJ_ANCHOR_SPAM"


class UnapprovedAgentPush(Exception):
    code = "RED_EWJ_UNAPPROVED_AGENT_PUSH"


def _load_rate() -> dict[str, Any]:
    if not RATE_PATH.exists():
        return {"important_timestamps": []}
    return json.loads(RATE_PATH.read_text(encoding="utf-8"))


def _save_rate(data: dict[str, Any]) -> None:
    RATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def check_rate_limit(cfg: WitnessJournalConfig, importance: WitnessImportanceClass) -> None:
    if importance not in {WitnessImportanceClass.IMPORTANT, WitnessImportanceClass.CRITICAL}:
        return
    data = _load_rate()
    now = time.time()
    window = [t for t in data.get("important_timestamps", []) if now - t < 3600]
    if len(window) >= cfg.max_important_per_hour:
        raise AnchorSpamBlocked(f"rate limit exceeded: {len(window)} important events in last hour")
    window.append(now)
    data["important_timestamps"] = window
    _save_rate(data)


def decide_append(
    cfg: WitnessJournalConfig,
    request: AnchorWriterRequest,
) -> tuple[WitnessAppendDecision, str]:
    if request.agent_requested and request.push_requested and not request.operator_invoked:
        return WitnessAppendDecision.DENY, "RED_EWJ_UNAPPROVED_AGENT_PUSH"

    if request.importance == WitnessImportanceClass.OPERATOR_PINNED:
        if request.operator_invoked:
            return (
                WitnessAppendDecision.ALLOW_LIVE_PUSH if request.push_requested and cfg.allow_push else WitnessAppendDecision.ALLOW_LOCAL_ONLY,
                "operator pinned marker",
            )
        return WitnessAppendDecision.QUEUE_FOR_OPERATOR, "operator pin requires operator invocation"

    if request.importance == WitnessImportanceClass.INCIDENT:
        return WitnessAppendDecision.QUEUE_FOR_OPERATOR, "incident markers require operator review"

    if request.importance == WitnessImportanceClass.RELEASE:
        return WitnessAppendDecision.QUEUE_FOR_OPERATOR, "release markers require operator review"

    if request.importance == WitnessImportanceClass.CRITICAL:
        if request.operator_invoked and request.push_requested and cfg.allow_push:
            return WitnessAppendDecision.ALLOW_LIVE_PUSH, "critical operator-approved push"
        return WitnessAppendDecision.QUEUE_FOR_OPERATOR, "critical events queue for operator"

    if request.importance == WitnessImportanceClass.IMPORTANT:
        if request.agent_requested and not request.operator_invoked:
            return WitnessAppendDecision.QUEUE_FOR_OPERATOR, "agent important marker queued for review"
        if request.operator_invoked:
            return (
                WitnessAppendDecision.ALLOW_LIVE_PUSH if request.push_requested and cfg.allow_push else WitnessAppendDecision.ALLOW_LOCAL_ONLY,
                "operator important marker",
            )
        return WitnessAppendDecision.QUEUE_FOR_OPERATOR, "important marker requires review"

    # ROUTINE lifecycle
    if is_lifecycle_event(request.event_class):
        if request.operator_invoked and request.push_requested and cfg.allow_push:
            return WitnessAppendDecision.ALLOW_LIVE_PUSH, "lifecycle operator push"
        return WitnessAppendDecision.ALLOW_LOCAL_ONLY, "lifecycle local witness default"

    if request.kind == AnchorWriterRequestKind.OPERATOR_APPEND and request.operator_invoked:
        return (
            WitnessAppendDecision.ALLOW_LIVE_PUSH if request.push_requested and cfg.allow_push else WitnessAppendDecision.ALLOW_LOCAL_ONLY,
            "operator append",
        )

    return WitnessAppendDecision.DENY, "event not allowed by policy"


def queue_for_operator(request: AnchorWriterRequest, *, reason: str) -> Path:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    if QUEUE_PATH.exists():
        items = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    entry = {
        "queued_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reason": reason,
        "event_class": request.event_class.value,
        "importance": request.importance.value,
        "summary": request.summary,
        "facts": request.facts,
        "mission_id": request.mission_id,
        "run_id": request.run_id,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    items.append(entry)
    QUEUE_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return QUEUE_PATH


__all__ = [
    "AnchorSpamBlocked",
    "LOCAL_STATE",
    "QUEUE_PATH",
    "UnapprovedAgentPush",
    "check_rate_limit",
    "decide_append",
    "queue_for_operator",
]
