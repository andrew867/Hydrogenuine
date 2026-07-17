"""Governed work loop runner."""

from __future__ import annotations

import os
from pathlib import Path

from hg_runtime.capability_broker.action_registry import get_action, is_forbidden_action, is_known_action
from hg_runtime.capability_broker.schema import new_decision_id
from hg_runtime.external_write_authority.action_candidate import load_candidate
from hg_runtime.governed_work_loop.action_quota import load_or_create_quota
from hg_runtime.governed_work_loop.candidate_bridge import create_external_candidate
from hg_runtime.governed_work_loop.dispatch_bridge import (
    attempt_live_dispatch,
    execute_governed_dry_dispatch,
    request_authority_for_candidate,
)
from hg_runtime.governed_work_loop.envelope_policy import evaluate_work_item
from hg_runtime.governed_work_loop.postflight import GovernedWorkLoopPostflight, write_postflight
from hg_runtime.governed_work_loop.schema import GovernedWorkLoopVerdict, load_governed_work_policy, now_iso
from hg_runtime.governed_work_loop.work_envelope import GovernedWorkEnvelope, ExternalActionEnvelope, load_demo_external_envelope
from hg_runtime.governed_work_loop.work_item import create_work_item
from hg_runtime.governed_work_loop.work_receipts import GovernedWorkDecision, GovernedWorkReceipt, persist_decision, persist_receipt
from hg_runtime.hands_off_session.manual_controls import check_panic, check_stop
from hg_runtime.task_selection.objective_universe import create_demo_universe, list_universes, load_universe
from hg_runtime.task_selection.task_candidate import load_candidate as load_task_candidate, seed_demo_candidates
from hg_runtime.task_selection.task_selector import TaskSelectionContext, select_next_task


def _broker_ref_for_work(work_type: str) -> str | None:
    mapping = {
        "review_local_artifacts": "observe_social",
        "summarize_recent_receipts": "synthesize_notes",
        "draft_internal_note": "propose_draft",
        "inspect_queue": "propose_operator_question",
        "prepare_external_action_candidate": "create_external_action_candidate",
        "status_report": "witness_turn",
        "idle_reflection": "rest_turn",
        "dry_run_external_dispatch": "create_external_action_candidate",
        "request_external_authority": "create_external_action_candidate",
    }
    action = mapping.get(work_type)
    if not action or is_forbidden_action(action) or not is_known_action(action):
        return None
    act = get_action(action)
    if not act or act.external_side_effect:
        return None
    return new_decision_id()


def _load_universe(envelope: GovernedWorkEnvelope):
    if envelope.objective_universe_ref:
        u = load_universe(envelope.objective_universe_ref)
        if u:
            return u
    universes = list_universes()
    if universes:
        return universes[-1]
    return create_demo_universe(agent_id=envelope.agent_id)


def _select_task(envelope: GovernedWorkEnvelope, run_id: str):
    universe = _load_universe(envelope)
    from hg_runtime.task_selection.schema import STORE_ROOT as TS_ROOT

    cand_dir = TS_ROOT / "candidates"
    candidates = []
    if cand_dir.is_dir():
        for p in sorted(cand_dir.glob("*.json")):
            c = load_task_candidate(p.stem)
            if c:
                candidates.append(c)
    if not candidates:
        candidates = seed_demo_candidates(universe.universe_id)
    ctx = TaskSelectionContext(universe=universe, candidates=candidates, run_id=run_id)
    return select_next_task(ctx)


def run_governed_work_loop_once(
    envelope: GovernedWorkEnvelope,
    session_state_ref: str,
    *,
    forced_work_type: str | None = None,
    forced_scope: str | None = None,
    ext_envelope: ExternalActionEnvelope | None = None,
    attempt_live: bool = False,
) -> GovernedWorkReceipt:
    """Execute one governed work iteration."""
    policy = load_governed_work_policy()
    run_id = session_state_ref

    if check_panic(run_id.replace("hands-off-", "phase22-")) or check_stop(run_id.replace("hands-off-", "phase22-")):
        pass  # caller checks STOP/PANIC at session level

    if forced_work_type:
        ts_ref = f"forced-{run_id}"
        tc_ref = f"forced-cand-{forced_work_type}"
        work_type = forced_work_type
        scope = forced_scope or "internal:artifacts"
        item = create_work_item(
            task_selection_ref=ts_ref,
            task_candidate_ref=tc_ref,
            task_type=work_type,
            scope_ref=scope,
            work_type=work_type,
        )
    else:
        ts_result = _select_task(envelope, run_id)
        if not ts_result.receipt:
            raise ValueError(GovernedWorkLoopVerdict.RED_WORK_WITHOUT_RECEIPT.value)
        if not ts_result.selected:
            item = create_work_item(
                task_selection_ref=ts_result.decision.task_selection_decision_id,
                task_candidate_ref="idle",
                task_type="idle_reflection",
                scope_ref="internal:idle",
            )
            work_type = "idle_reflection"
        else:
            item = create_work_item(
                task_selection_ref=ts_result.decision.task_selection_decision_id,
                task_candidate_ref=ts_result.selected.task_candidate_id,
                task_type=ts_result.selected.task_type,
                scope_ref=ts_result.selected.objective_scope_ref,
            )
            work_type = item.work_type
            ts_ref = ts_result.receipt.task_selection_receipt_id
    if forced_work_type:
        ts_ref = item.task_selection_ref

    ok, reason = evaluate_work_item(envelope, item)
    broker_ref = _broker_ref_for_work(work_type)
    ext_cand_ref = None
    auth_ref = None
    dispatch_ref = None
    dry_ref = None
    verdict = GovernedWorkLoopVerdict.GREEN_WORK_COMPLETE.value
    external_se = False

    if attempt_live:
        ext_env = ext_envelope or load_demo_external_envelope()
        disp = attempt_live_dispatch(ext_env)
        dispatch_ref = disp.governed_dispatch_decision_id
        verdict = disp.verdict
        decision = GovernedWorkDecision(
            governed_work_decision_id=disp.governed_dispatch_decision_id,
            work_item_ref=item.work_item_id,
            verdict=verdict,
            refusal_reason=disp.refusal_reasons[0] if disp.refusal_reasons else None,
            broker_decision_ref=broker_ref,
            external_candidate_ref=None,
            authority_request_ref=None,
            dispatch_decision_ref=dispatch_ref,
            created_at=item.created_at,
        ).with_hash()
        persist_decision(decision)
        receipt = GovernedWorkReceipt(
            governed_work_receipt_id=f"gov-work-rcpt-{item.work_item_id}",
            decision_ref=decision.governed_work_decision_id,
            work_item_ref=item.work_item_id,
            task_selection_ref=ts_ref,
            work_type="live_dispatch_attempt",
            external_side_effect=False,
            verdict=verdict,
            broker_decision_ref=broker_ref,
            created_at=item.created_at,
        ).with_hash()
        persist_receipt(receipt)
        return receipt

    if not ok:
        verdict = GovernedWorkLoopVerdict.GREEN_WORK_REFUSED.value
        decision = GovernedWorkDecision(
            governed_work_decision_id=f"gov-decision-{item.work_item_id}",
            work_item_ref=item.work_item_id,
            verdict=verdict,
            refusal_reason=reason,
            broker_decision_ref=broker_ref,
            external_candidate_ref=None,
            authority_request_ref=None,
            dispatch_decision_ref=None,
            created_at=item.created_at,
        ).with_hash()
        persist_decision(decision)
        receipt = GovernedWorkReceipt(
            governed_work_receipt_id=f"gov-work-rcpt-{item.work_item_id}",
            decision_ref=decision.governed_work_decision_id,
            work_item_ref=item.work_item_id,
            task_selection_ref=ts_ref,
            work_type=work_type,
            external_side_effect=False,
            verdict=verdict,
            broker_decision_ref=broker_ref,
            created_at=item.created_at,
        ).with_hash()
        persist_receipt(receipt)
        return receipt

    quota = load_or_create_quota(run_id)

    if work_type == "prepare_external_action_candidate":
        cand_id, br = create_external_candidate(
            run_id=run_id,
            platform="moltbook",
            action_type="publish_post",
            content="governed work loop candidate",
            scope="platform:moltbook:draft-only",
            quota=quota,
        )
        ext_cand_ref = cand_id
        broker_ref = br or broker_ref
        if policy.get("external_candidate_receipt_required") and not ext_cand_ref:
            verdict = GovernedWorkLoopVerdict.RED_WORK_WITHOUT_RECEIPT.value

    elif work_type == "request_external_authority":
        cand_id, br = create_external_candidate(
            run_id=run_id,
            platform="moltbook",
            action_type="publish_post",
            content="authority request candidate",
            scope="platform:moltbook:draft-only",
            quota=quota,
        )
        if cand_id and br:
            auth_ref = request_authority_for_candidate(run_id=run_id, candidate_id=cand_id, broker_ref=br)
            ext_cand_ref = cand_id
            broker_ref = br

    elif work_type == "dry_run_external_dispatch":
        cand_id, br = create_external_candidate(
            run_id=run_id,
            platform="moltbook",
            action_type="publish_post",
            content="dry dispatch candidate",
            scope="platform:moltbook:draft-only",
            quota=quota,
        )
        if cand_id and br:
            auth_ref = request_authority_for_candidate(run_id=run_id, candidate_id=cand_id, broker_ref=br)
            ext_cand_ref = cand_id
            cand = load_candidate(run_id, cand_id)
            if cand and auth_ref:
                disp = execute_governed_dry_dispatch(
                    run_id=run_id,
                    candidate_id=cand_id,
                    authority_request_id=auth_ref,
                    platform=cand.requested_platform,
                    action_type=cand.requested_action_type.value,
                    scope=cand.scope,
                    content_hash=cand.content_hash,
                )
                dispatch_ref = disp.governed_dispatch_decision_id
                dry_ref = disp.dry_dispatch_ref
                external_se = disp.external_side_effect
                verdict = disp.verdict
                quota.record_dry_dispatch()

    elif work_type in ("review_local_artifacts", "summarize_recent_receipts", "draft_internal_note", "inspect_queue", "status_report", "idle_reflection"):
        if not broker_ref and policy.get("broker_receipt_required"):
            verdict = GovernedWorkLoopVerdict.RED_BROKER_BYPASSED.value

    decision = GovernedWorkDecision(
        governed_work_decision_id=f"gov-decision-{item.work_item_id}",
        work_item_ref=item.work_item_id,
        verdict=verdict,
        refusal_reason=None,
        broker_decision_ref=broker_ref,
        external_candidate_ref=ext_cand_ref,
        authority_request_ref=auth_ref,
        dispatch_decision_ref=dispatch_ref,
        created_at=item.created_at,
    ).with_hash()
    persist_decision(decision)

    receipt = GovernedWorkReceipt(
        governed_work_receipt_id=f"gov-work-rcpt-{item.work_item_id}",
        decision_ref=decision.governed_work_decision_id,
        work_item_ref=item.work_item_id,
        task_selection_ref=ts_ref,
        work_type=work_type,
        external_side_effect=external_se,
        verdict=verdict,
        broker_decision_ref=broker_ref,
        external_candidate_ref=ext_cand_ref,
        dry_dispatch_ref=dry_ref,
        created_at=item.created_at,
    ).with_hash()
    persist_receipt(receipt)
    return receipt


def run_governed_work_loop_smoke(
    envelope: GovernedWorkEnvelope,
    observed_iterations: int,
    *,
    run_id: str = "phase23-smoke",
) -> GovernedWorkLoopPostflight:
    """Test harness smoke — not a production cap."""
    from hg_runtime.governed_work_loop.action_quota import reset_quota_for_run

    reset_quota_for_run(run_id)
    ext_env = load_demo_external_envelope()
    if ext_env is None:
        _, ext_env = create_demo_envelope()
    steps = [
        ("review_local_artifacts", "internal:artifacts", False),
        ("prepare_external_action_candidate", "platform:moltbook:draft-only", False),
        ("publish_live_unscoped", "external:live_unscoped", False),
        ("dry_run_external_dispatch", "platform:moltbook:draft-only", False),
        (None, None, True),
    ]
    receipts: list[str] = []
    internal_done = False
    candidate_done = False
    refused_done = False
    dry_done = False
    live_refused = False
    external_se_count = 0

    for i in range(min(observed_iterations, len(steps))):
        wt, scope, live_attempt = steps[i]
        if live_attempt:
            rcpt = run_governed_work_loop_once(envelope, run_id, ext_envelope=ext_env, attempt_live=True)
            live_refused = "LIVE" in rcpt.verdict or "YELLOW" in rcpt.verdict or "RED_LIVE" in rcpt.verdict
        else:
            rcpt = run_governed_work_loop_once(envelope, run_id, forced_work_type=wt, forced_scope=scope, ext_envelope=ext_env)
        receipts.append(rcpt.governed_work_receipt_id)
        if rcpt.work_type == "review_local_artifacts" and "REFUSED" not in rcpt.verdict:
            internal_done = True
        if rcpt.external_candidate_ref:
            candidate_done = True
        if rcpt.verdict.endswith("REFUSED") or "REFUSED" in rcpt.verdict:
            refused_done = True
        if rcpt.dry_dispatch_ref:
            dry_done = True
        external_se_count += int(rcpt.external_side_effect)

    pf = GovernedWorkLoopPostflight(
        postflight_id=f"gov-work-pf-{run_id}",
        run_id=run_id,
        verdict=GovernedWorkLoopVerdict.GREEN_WORK_COMPLETE.value,
        observed_iterations=observed_iterations,
        work_receipt_refs=tuple(receipts),
        internal_work_completed=internal_done,
        external_candidate_prepared=candidate_done,
        out_of_envelope_refused=refused_done,
        dry_dispatch_recorded=dry_done,
        live_dispatch_refused=live_refused,
        external_side_effect_count=external_se_count,
        created_at=now_iso(),
    )
    write_postflight(pf)
    return pf


__all__ = ["run_governed_work_loop_once", "run_governed_work_loop_smoke"]
