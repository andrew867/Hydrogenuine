"""Lifecycle anchor autopilot dispatcher."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from hg_runtime.external_witness_journal.agent0_context import load_journal_config
from hg_runtime.external_witness_journal.anchor_writer import append_journal_event
from hg_runtime.external_witness_journal.importance import default_importance_for_event
from hg_runtime.external_witness_journal.schema import (
    AnchorWriterRequest,
    AnchorWriterRequestKind,
    FORBIDDEN_PUBLIC_FRAGMENTS,
    WitnessImportanceClass,
)
from hg_runtime.lifecycle_anchor_autopilot.policy import decide_lifecycle_autopilot, load_policy
from hg_runtime.lifecycle_anchor_autopilot.queue import enqueue
from hg_runtime.lifecycle_anchor_autopilot.receipts import build_receipt
from hg_runtime.lifecycle_anchor_autopilot.schema import (
    AnchorAutopilotMode,
    AnchorAutopilotQueueItem,
    LifecycleAnchorEvent,
    LIFECYCLE_TO_WITNESS,
)

WORKSPACE = Path(__file__).resolve().parents[2]
STATE_PATH = WORKSPACE / ".hg-local/lifecycle_anchor_autopilot/state.json"

_SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|token|password|bearer|private[_-]?key)")


def _sanitize_text(text: str) -> str:
    lowered = text.lower()
    for frag in FORBIDDEN_PUBLIC_FRAGMENTS:
        if frag in lowered:
            raise ValueError("RED_SECRET_EXPOSURE")
    if _SECRET_RE.search(text):
        raise ValueError("RED_SECRET_EXPOSURE")
    if len(text) > 2000:
        return text[:2000] + "…"
    return text


def _sanitize_facts(facts: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(facts)
    _sanitize_text(raw)
    clean: dict[str, Any] = {}
    for key, value in facts.items():
        if key.startswith("_"):
            continue
        if any(x in str(key).lower() for x in ("secret", "password", "token", "private_key", "prompt")):
            continue
        if isinstance(value, str):
            clean[key] = _sanitize_text(value)
        elif isinstance(value, (int, float, bool)) or value is None:
            clean[key] = value
        else:
            clean[key] = _sanitize_text(json.dumps(value)[:500])
    return clean


def _save_state(payload: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def dispatch_lifecycle_event(
    event: LifecycleAnchorEvent,
    summary: str,
    *,
    facts: dict[str, Any] | None = None,
    importance: WitnessImportanceClass | None = None,
    agent_requested: bool = False,
    operator_invoked: bool = False,
    push_requested: bool = False,
    anchor_handoff: dict[str, Any] | None = None,
    proof_ref: str | None = None,
    mission_id: str | None = None,
    run_id: str | None = None,
    config_path: str | Path | None = None,
    dry_run: bool = False,
    workspace: Path | None = None,
) -> dict[str, Any]:
    policy = load_policy()
    witness_class = LIFECYCLE_TO_WITNESS[event]
    importance = importance or default_importance_for_event(witness_class)
    safe_summary = _sanitize_text(summary)
    safe_facts = _sanitize_facts(facts or {})

    decision = decide_lifecycle_autopilot(
        event,
        policy=policy,
        agent_requested=agent_requested,
        operator_invoked=operator_invoked,
        push_requested=push_requested,
        importance=importance,
        witness_event=witness_class,
    )

    if decision.mode == AnchorAutopilotMode.DENY:
        receipt = build_receipt(event_class=event.value, decision=decision)
        return receipt.to_payload()

    if decision.mode == AnchorAutopilotMode.QUEUE_FOR_OPERATOR:
        item = AnchorAutopilotQueueItem(
            item_id=f"aq-{uuid.uuid4().hex[:12]}",
            event_class=event.value,
            summary=safe_summary,
            facts=safe_facts,
            queued_reason=decision.reason,
            agent_requested=agent_requested,
        )
        enqueue(item)
        receipt = build_receipt(event_class=event.value, decision=decision, queue_item_id=item.item_id)
        return receipt.to_payload()

    cfg = load_journal_config(config_path) if config_path else load_journal_config()
    request = AnchorWriterRequest(
        kind=AnchorWriterRequestKind.OPERATOR_APPEND,
        event_class=witness_class,
        importance=importance,
        summary=safe_summary,
        facts=safe_facts,
        operator_invoked=operator_invoked or not agent_requested,
        push_requested=decision.push_allowed and push_requested,
        agent_requested=agent_requested,
        mission_id=mission_id,
        run_id=run_id,
        proof_ref=proof_ref,
        anchor_handoff=anchor_handoff,
    )
    dry_run = dry_run or decision.mode == AnchorAutopilotMode.DENY
    push = decision.mode == AnchorAutopilotMode.LIVE_PUSH and push_requested and not dry_run
    try:
        result = append_journal_event(
            cfg, request, dry_run=dry_run, push=push, run_id=run_id or "", workspace=workspace or WORKSPACE
        )
    except ValueError as exc:
        if "RED_SECRET" in str(exc):
            decision = decide_lifecycle_autopilot(event, policy=policy)
            decision.mode = AnchorAutopilotMode.DENY
            decision.verdict = "RED_SECRET_EXPOSURE"
            receipt = build_receipt(event_class=event.value, decision=decision)
            return receipt.to_payload()
        raise

    receipt = build_receipt(
        event_class=event.value,
        decision=decision,
        local_committed=result.receipt is not None,
        pushed=bool(result.receipt and result.receipt.pushed),
        journal_receipt_id=result.receipt.receipt_id if result.receipt else None,
    )
    payload = receipt.to_payload()
    payload["anchor_writer_result"] = {
        "decision": result.decision.verdict,
        "receipt": result.receipt.to_dict() if result.receipt else None,
    }
    _save_state({"last_event": event.value, "last_receipt": payload})
    return payload
