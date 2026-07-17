"""Task selector — model proposes, broker disposes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.task_selection.idle_reflection import perform_idle_reflection
from hg_runtime.task_selection.objective_universe import ObjectiveUniverse
from hg_runtime.task_selection.schema import (
    TaskRefusalReason,
    TaskSelectionVerdict,
    load_task_selection_policy,
    new_id,
    now_iso,
)
from hg_runtime.task_selection.task_candidate import TaskCandidate
from hg_runtime.task_selection.task_policy import evaluate_candidate_policy
from hg_runtime.task_selection.task_receipts import (
    TaskSelectionDecision,
    TaskSelectionReceipt,
    TaskSwitchReceipt,
    persist_decision,
    persist_selection_receipt,
    persist_switch_receipt,
)


@dataclass
class TaskSelectionContext:
    universe: ObjectiveUniverse
    candidates: list[TaskCandidate]
    run_id: str
    stop_panic_clear: bool = True
    prior_selected_ref: str | None = None
    model_suggestions: list[str] | None = None
    live_read_cargo: str | None = None


@dataclass
class TaskSelectionResult:
    decision: TaskSelectionDecision
    receipt: TaskSelectionReceipt | None
    switch_receipt: TaskSwitchReceipt | None
    verdict: TaskSelectionVerdict
    selected: TaskCandidate | None
    refused: list[tuple[str, TaskRefusalReason]]


AUTHORITY_BOUNDARY_REF = "configs/agent_zero/external_write_authority_policy.json"


def _check_stop_panic() -> bool:
    import os

    if os.environ.get("HG_STOP_REQUESTED") == "1":
        return False
    if os.environ.get("HG_PANIC_REQUESTED") == "1":
        return False
    return True


def _broker_ref_for_task(task_type: str) -> str | None:
    """Map selected internal task to broker mediation — no bypass."""
    mapping = {
        "review_local_artifacts": "observe_social",
        "summarize_recent_receipts": "synthesize_notes",
        "draft_internal_note": "propose_draft",
        "inspect_queue": "propose_operator_question",
        "prepare_external_action_candidate": "create_external_action_candidate",
        "run_local_status_check": "witness_turn",
        "idle_reflection": "rest_turn",
    }
    action = mapping.get(task_type)
    if not action:
        return None
    from hg_runtime.capability_broker.action_registry import get_action, is_forbidden_action, is_known_action
    from hg_runtime.capability_broker.schema import new_decision_id

    if is_forbidden_action(action) or not is_known_action(action):
        return None
    act = get_action(action)
    if not act or act.external_side_effect:
        return None
    return new_decision_id()


def select_next_task(ctx: TaskSelectionContext) -> TaskSelectionResult:
    policy = load_task_selection_policy()
    if not ctx.stop_panic_clear or not _check_stop_panic():
        decision = TaskSelectionDecision(
            task_selection_decision_id=new_id("task-decision"),
            universe_ref=ctx.universe.universe_id,
            candidate_refs=tuple(c.task_candidate_id for c in ctx.candidates),
            refused_candidate_refs=(),
            deferred_candidate_refs=(),
            selection_reason_code="stop_panic_active",
            authority_boundary_ref=AUTHORITY_BOUNDARY_REF,
            verdict=TaskSelectionVerdict.RED_STOP_PANIC_NOT_CHECKED.value,
            created_at=now_iso(),
        ).with_hash()
        persist_decision(decision)
        return TaskSelectionResult(
            decision=decision,
            receipt=None,
            switch_receipt=None,
            verdict=TaskSelectionVerdict.RED_STOP_PANIC_NOT_CHECKED,
            selected=None,
            refused=[],
        )

    refused: list[tuple[str, TaskRefusalReason]] = []
    deferred: list[str] = []
    valid: list[TaskCandidate] = []

    live_command = False
    if ctx.live_read_cargo:
        cargo_lower = ctx.live_read_cargo.lower()
        if any(x in cargo_lower for x in ("publish now", "send immediately", "execute live", "bypass broker")):
            live_command = True

    sorted_candidates = sorted(ctx.candidates, key=lambda c: c.task_candidate_id)

    for cand in sorted_candidates:
        scope_ok = ctx.universe.scope_allowed(cand.objective_scope_ref)
        ok, reason = evaluate_candidate_policy(
            task_type=cand.task_type,
            objective_scope=cand.objective_scope_ref,
            scope_allowed=scope_ok,
            requires_external_action=cand.requires_external_action,
            live_read_command=live_command,
        )
        if not ok and reason:
            refused.append((cand.task_candidate_id, reason))
        elif ok:
            valid.append(cand)

    if not valid:
        idle = perform_idle_reflection(
            universe_ref=ctx.universe.universe_id,
            reason_code="empty_queue" if not ctx.candidates else "all_refused",
        )
        decision = TaskSelectionDecision(
            task_selection_decision_id=new_id("task-decision"),
            universe_ref=ctx.universe.universe_id,
            candidate_refs=tuple(c.task_candidate_id for c in ctx.candidates),
            refused_candidate_refs=tuple(r[0] for r in refused),
            deferred_candidate_refs=tuple(deferred),
            idle_reflection_ref=idle.receipt.idle_reflection_receipt_id,
            selection_reason_code=idle.reason_code,
            authority_boundary_ref=AUTHORITY_BOUNDARY_REF,
            verdict=idle.verdict.value,
            created_at=now_iso(),
        ).with_hash()
        persist_decision(decision)
        receipt = None
        if policy.get("task_selection_receipt_required", True):
            receipt = TaskSelectionReceipt(
                task_selection_receipt_id=new_id("task-sel-receipt"),
                decision_ref=decision.task_selection_decision_id,
                selected_candidate_ref=None,
                external_action_required=False,
                external_action_allowed=False,
                created_at=now_iso(),
            ).with_hash()
            persist_selection_receipt(receipt)
        return TaskSelectionResult(
            decision=decision,
            receipt=receipt,
            switch_receipt=None,
            verdict=idle.verdict,
            selected=None,
            refused=refused,
        )

    selected = valid[0]
    broker_ref = _broker_ref_for_task(selected.task_type)
    decision = TaskSelectionDecision(
        task_selection_decision_id=new_id("task-decision"),
        universe_ref=ctx.universe.universe_id,
        candidate_refs=tuple(c.task_candidate_id for c in ctx.candidates),
        selected_candidate_ref=selected.task_candidate_id,
        refused_candidate_refs=tuple(r[0] for r in refused),
        deferred_candidate_refs=tuple(deferred),
        selection_reason_code="deterministic_first_valid",
        authority_boundary_ref=AUTHORITY_BOUNDARY_REF,
        broker_decision_ref=broker_ref,
        verdict=TaskSelectionVerdict.GREEN_TASK_SELECTED.value,
        created_at=now_iso(),
    ).with_hash()
    persist_decision(decision)

    ext_required = selected.requires_external_action
    ext_allowed = bool(policy.get("external_side_effects_allowed", False) and not ext_required)
    receipt = TaskSelectionReceipt(
        task_selection_receipt_id=new_id("task-sel-receipt"),
        decision_ref=decision.task_selection_decision_id,
        selected_candidate_ref=selected.task_candidate_id,
        objective_scope_ref=selected.objective_scope_ref,
        task_type=selected.task_type,
        external_action_required=ext_required,
        external_action_allowed=ext_allowed,
        created_at=now_iso(),
    ).with_hash()
    persist_selection_receipt(receipt)

    switch = None
    if ctx.prior_selected_ref and ctx.prior_selected_ref != selected.task_candidate_id:
        switch = TaskSwitchReceipt(
            task_switch_receipt_id=new_id("task-switch"),
            from_task_ref=ctx.prior_selected_ref,
            to_task_ref=selected.task_candidate_id,
            decision_ref=decision.task_selection_decision_id,
            created_at=now_iso(),
        ).with_hash()
        persist_switch_receipt(switch)

    return TaskSelectionResult(
        decision=decision,
        receipt=receipt,
        switch_receipt=switch,
        verdict=TaskSelectionVerdict.GREEN_TASK_SELECTED,
        selected=selected,
        refused=refused,
    )


def refuse_out_of_scope_candidate(
    ctx: TaskSelectionContext,
    *,
    task_type: str,
    objective_scope: str,
) -> TaskSelectionResult:
    """Explicit refusal path for smoke tests."""
    from hg_runtime.task_selection.task_candidate import create_candidate

    cand = create_candidate(
        objective_scope=objective_scope,
        task_type=task_type,
        title=f"refused:{task_type}",
    )
    ctx.candidates = [cand]
    return select_next_task(ctx)


def attach_task_selection_to_turn_payload(payload: dict[str, Any], result: TaskSelectionResult) -> dict[str, Any]:
    """Attach task selection refs to agent turn receipt payload."""
    out = dict(payload)
    out["task_selection_decision_ref"] = result.decision.task_selection_decision_id
    if result.receipt:
        out["task_selection_receipt_ref"] = result.receipt.task_selection_receipt_id
    if result.selected:
        out["selected_task_type"] = result.selected.task_type
    return out
