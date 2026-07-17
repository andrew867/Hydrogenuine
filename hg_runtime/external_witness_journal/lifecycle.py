"""Lifecycle hook helpers for witness journal appends."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.external_witness_journal.anchor_writer import AnchorWriterResult, append_journal_event
from hg_runtime.external_witness_journal.agent0_context import load_journal_config
from hg_runtime.external_witness_journal.importance import is_lifecycle_event
from hg_runtime.lifecycle_anchor_autopilot.dispatcher import dispatch_lifecycle_event
from hg_runtime.lifecycle_anchor_autopilot.schema import LIFECYCLE_TO_WITNESS, LifecycleAnchorEvent
from hg_runtime.external_witness_journal.schema import (
    AnchorWriterRequest,
    AnchorWriterRequestKind,
    WitnessEventClass,
    WitnessImportanceClass,
)

WORKSPACE = Path(__file__).resolve().parents[2]


def _load_handoff(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _lifecycle_event_for_witness(event_class: WitnessEventClass) -> LifecycleAnchorEvent | None:
    for life, witness in LIFECYCLE_TO_WITNESS.items():
        if witness == event_class:
            return life
    return None


def _wrap_autopilot(payload: dict[str, Any]) -> AnchorWriterResult:
    from hg_runtime.external_witness_journal.schema import AnchorWriterDecision, WitnessAppendDecision

    awr = payload.get("anchor_writer_result")
    if awr and awr.get("receipt"):
        from hg_runtime.external_witness_journal.receipts import AnchorWriterReceipt

        r = awr["receipt"]
        receipt = AnchorWriterReceipt(
            receipt_id=r["receipt_id"],
            run_id=r.get("run_id", ""),
            event_class=r.get("event_class", payload.get("event_class", "")),
            event_sequence=r.get("event_sequence", 0),
            journal_event_sha256=r.get("journal_event_sha256", ""),
            decision=WitnessAppendDecision(r.get("decision", "ALLOW_LOCAL_ONLY")),
            pushed=bool(r.get("pushed")),
            dry_run=bool(r.get("dry_run")),
            github_commit_sha=r.get("github_commit_sha"),
            queue_path=r.get("queue_path"),
        )
        decision = AnchorWriterDecision(
            decision=receipt.decision,
            verdict=str(awr.get("decision", payload.get("decision", {}).get("verdict", ""))),
            reason=payload.get("decision", {}).get("reason", ""),
            allow_push=receipt.pushed,
        )
        from hg_runtime.external_witness_journal.schema import WitnessJournalBundle

        bundle = WitnessJournalBundle(
            event_class=WitnessEventClass(r.get("event_class", "FIRST_WAKE_START")),
            event_sequence=int(r.get("event_sequence", 0)),
            journal_event_sha256=r.get("journal_event_sha256", ""),
        )
        return AnchorWriterResult(decision=decision, bundle=bundle, receipt=receipt)

    decision_payload = payload.get("decision", {})
    mode = decision_payload.get("mode", "LOCAL_ONLY")
    mapping = {
        "LOCAL_ONLY": WitnessAppendDecision.ALLOW_LOCAL_ONLY,
        "LIVE_PUSH": WitnessAppendDecision.ALLOW_LIVE_PUSH,
        "QUEUE_FOR_OPERATOR": WitnessAppendDecision.QUEUE_FOR_OPERATOR,
        "DENY": WitnessAppendDecision.DENY,
    }
    decision = AnchorWriterDecision(
        decision=mapping.get(mode, WitnessAppendDecision.ALLOW_LOCAL_ONLY),
        verdict=decision_payload.get("verdict", "GREEN_LIFECYCLE_ANCHOR_AUTOPILOT_READY"),
        reason=decision_payload.get("reason", ""),
        allow_push=bool(decision_payload.get("push_allowed")),
    )
    receipt = None
    if payload.get("journal_receipt_id"):
        pass
    return AnchorWriterResult(decision=decision, bundle=None, receipt=receipt)


def append_lifecycle_event(
    event_class: WitnessEventClass,
    summary: str,
    *,
    importance: WitnessImportanceClass = WitnessImportanceClass.ROUTINE,
    facts: dict[str, Any] | None = None,
    mission_id: str | None = None,
    run_id: str | None = None,
    proof_ref: str | None = None,
    anchor_handoff_path: str | Path | None = None,
    epoch_id: str | None = None,
    epoch_lock_id: str | None = None,
    operator_invoked: bool = False,
    push: bool = False,
    dry_run: bool = True,
    config_path: str | Path | None = None,
    workspace: Path | None = None,
) -> AnchorWriterResult:
    life = _lifecycle_event_for_witness(event_class)
    if life is not None and is_lifecycle_event(event_class):
        payload = dispatch_lifecycle_event(
            life,
            summary,
            facts=facts,
            importance=importance,
            agent_requested=not operator_invoked,
            operator_invoked=operator_invoked,
            push_requested=push and not dry_run,
            anchor_handoff=_load_handoff(anchor_handoff_path),
            proof_ref=proof_ref,
            mission_id=mission_id,
            run_id=run_id,
            config_path=config_path,
            dry_run=dry_run,
            workspace=workspace,
        )
        return _wrap_autopilot(payload)
    cfg = load_journal_config(config_path) if config_path else load_journal_config()
    request = AnchorWriterRequest(
        kind=AnchorWriterRequestKind.OPERATOR_APPEND,
        event_class=event_class,
        importance=importance,
        summary=summary,
        facts=facts or {},
        operator_invoked=operator_invoked,
        push_requested=push,
        mission_id=mission_id,
        run_id=run_id,
        proof_ref=proof_ref,
        anchor_handoff=_load_handoff(anchor_handoff_path),
        epoch_id=epoch_id,
        epoch_lock_id=epoch_lock_id,
    )
    return append_journal_event(cfg, request, dry_run=dry_run, push=push, run_id=run_id or "", workspace=workspace)


def append_wake_refresh_start(**kwargs: Any) -> AnchorWriterResult:
    return append_lifecycle_event(
        WitnessEventClass.WAKE_REFRESH_START,
        kwargs.pop("summary", "Wake refresh cycle starting."),
        **kwargs,
    )


def append_wake_refresh_complete(verdict: str, **kwargs: Any) -> AnchorWriterResult:
    facts = kwargs.pop("facts", {})
    facts = {**facts, "wake_readiness": verdict}
    importance = WitnessImportanceClass.IMPORTANT if verdict.startswith("YELLOW") else WitnessImportanceClass.ROUTINE
    return append_lifecycle_event(
        WitnessEventClass.WAKE_REFRESH_COMPLETE,
        kwargs.pop("summary", f"Wake refresh complete: {verdict}."),
        importance=importance,
        facts=facts,
        **kwargs,
    )


def append_sleep_start(**kwargs: Any) -> AnchorWriterResult:
    return append_lifecycle_event(
        WitnessEventClass.SLEEP_START,
        kwargs.pop("summary", "Agent Zero sleep/shutdown starting."),
        **kwargs,
    )


def append_sleep_complete(**kwargs: Any) -> AnchorWriterResult:
    return append_lifecycle_event(
        WitnessEventClass.SLEEP_COMPLETE,
        kwargs.pop("summary", "Agent Zero sleep/shutdown complete."),
        **kwargs,
    )


def append_first_wake_start(**kwargs: Any) -> AnchorWriterResult:
    return append_lifecycle_event(
        WitnessEventClass.FIRST_WAKE_START,
        kwargs.pop("summary", "Agent Zero first wake mission starting."),
        **kwargs,
    )


def append_first_wake_complete(verdict: str, **kwargs: Any) -> AnchorWriterResult:
    facts = kwargs.pop("facts", {})
    facts = {**facts, "mission_verdict": verdict}
    return append_lifecycle_event(
        WitnessEventClass.FIRST_WAKE_COMPLETE,
        kwargs.pop("summary", f"Agent Zero first wake mission complete: {verdict}."),
        importance=WitnessImportanceClass.IMPORTANT,
        facts=facts,
        **kwargs,
    )


def append_weather_voice_start(**kwargs: Any) -> AnchorWriterResult:
    return append_lifecycle_event(
        WitnessEventClass.WEATHER_VOICE_START,
        kwargs.pop("summary", "Weather voice mission starting."),
        **kwargs,
    )


def append_weather_voice_complete(verdict: str, **kwargs: Any) -> AnchorWriterResult:
    facts = kwargs.pop("facts", {})
    facts = {**facts, "mission_verdict": verdict}
    return append_lifecycle_event(
        WitnessEventClass.WEATHER_VOICE_COMPLETE,
        kwargs.pop("summary", f"Weather voice mission complete: {verdict}."),
        facts=facts,
        **kwargs,
    )


__all__ = [
    "append_first_wake_complete",
    "append_first_wake_start",
    "append_lifecycle_event",
    "append_sleep_complete",
    "append_sleep_start",
    "append_wake_refresh_complete",
    "append_wake_refresh_start",
    "append_weather_voice_complete",
    "append_weather_voice_start",
]
