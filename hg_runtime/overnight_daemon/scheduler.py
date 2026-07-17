"""Daemon scheduler — the main loop that owns the overnight soak cycle.

Heartbeats, STOP/PANIC checks, check-ins, checkpoints, boundary scans,
autopilot proposals, subagent task execution, receipt writing.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from hg_runtime.live_local.client import infer_with_retry
from hg_runtime.live_local.compact_prompts import (
    compact_falsification_prompt, compact_boring_prompt,
    compact_units_prompt, compact_public_explainer_prompt,
)
from hg_runtime.overnight_qa.research_seeds import build_research_seeds, get_seed
from hg_runtime.overnight_qa.research_seed_queue import (
    zero_rank_seeds, runtime_select,
)
from hg_runtime.profile_model_autopilot.proposal import propose, dispose
from hg_runtime.profile_model_autopilot.profile_selector import select_profiles_for_mode
from hg_runtime.profile_model_autopilot.falsification import build_falsification_targets

from .config import DaemonConfig
from .state import RunState, save_state
from .heartbeat import write_heartbeat
from .stop_panic import stop_requested, panic_requested, checkin_requested
from .checkins import checkin_due, write_checkin
from .subagents import (
    SubagentTask, WorkerPool, create_task, SUBAGENT_ROLES,
    is_registered_subagent_role,
)
from .role_mapping import resolve_subagent_role
from .model_role_routing import (
    route_task, get_model_role, get_role_policy,
    gemma_tiny_prompt_for_mode, build_synthesis_prompt,
    SeedModeFailureTracker, ModelRouteDecision,
    GEMMA_MODEL_ID,
)
from .large_model_trial import (
    select_large_trial_candidate, build_large_trial_task,
    evaluate_large_trial_result, run_resource_preflight,
    default_large_trial_policy, LargeTrialPolicy,
)

_PROMPT = {
    "falsification_design": lambda s: compact_falsification_prompt(
        s.short_name or s.seed_id, s.seed_text),
    "boring_explanation_first": lambda s: compact_boring_prompt(
        s.short_name or s.seed_id, s.seed_text),
    "units_and_math_audit": lambda s: compact_units_prompt(
        s.short_name or s.seed_id, s.seed_text),
    "public_safe_explainer": lambda s: compact_public_explainer_prompt(
        s.short_name or s.seed_id, s.seed_text),
}

_SCIENCE_CYCLE = [
    "falsification_design", "boring_explanation_first",
    "units_and_math_audit", "public_safe_explainer",
]

_PRIORITY_SEEDS = [
    "electron_hole_spin_state_change_hypothesis",
    "observer_state_frequency_hypothesis",
    "quasiparticle_bridge_theory_requirements",
]


def _append_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            obj = asdict(r) if hasattr(r, "__dataclass_fields__") else r
            f.write(json.dumps(obj, default=str) + "\n")


def _pick_next_seed(state: RunState, seeds: list) -> str | None:
    for sid in _PRIORITY_SEEDS:
        if sid not in state.seeds_worked:
            return sid
    for s in seeds:
        if s.seed_id not in state.seeds_worked and s.seed_id not in state.seeds_skipped:
            if s.priority_hint == "high":
                return s.seed_id
    for s in seeds:
        if s.seed_id not in state.seeds_worked and s.seed_id not in state.seeds_skipped:
            return s.seed_id
    return None


def run_cycle(cfg: DaemonConfig, state: RunState, proof_dir: Path,
              pool: WorkerPool, *, log_fn=None) -> str:
    """Run one scheduler cycle. Returns 'continue', 'stop', 'panic', or 'completed'."""
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    start_time_epoch = time.time() - state.elapsed_seconds

    def _log(msg):
        if log_fn:
            log_fn(msg)

    def _heartbeat(**kw):
        write_heartbeat(
            cfg.state_dir, run_id=cfg.run_id, pid=os.getpid(),
            started_at=state.started_at, cycle_count=state.cycle_count,
            current_seed_id=state.current_seed_id,
            current_task_id=state.current_task_id,
            current_model=state.current_model,
            current_status=state.status,
            current_verdict_so_far=state.verdict_so_far,
            proof_path=str(proof_dir),
            stop_requested=stop_requested(cfg.state_dir),
            panic_requested=panic_requested(cfg.state_dir),
            receipt_count=state.receipt_count,
            boundary_violation_count=state.boundary_violations,
            **kw,
        )

    # --- heartbeat ---
    _heartbeat()

    # --- STOP / PANIC ---
    if panic_requested(cfg.state_dir):
        state.status = "panicked"
        state.verdict_so_far = "RED_PANIC_STOP"
        _log("PANIC requested — stopping immediately")
        return "panic"

    if stop_requested(cfg.state_dir):
        state.status = "stopped"
        state.verdict_so_far = "YELLOW_STOPPED_BY_OPERATOR"
        _log("STOP requested — finishing")
        return "stop"

    # --- elapsed check ---
    state.elapsed_seconds = time.time() - start_time_epoch
    if state.elapsed_seconds >= cfg.target_seconds():
        _log(f"Target duration reached ({cfg.duration_hours}h)")
        return "completed"

    if state.cycle_count >= cfg.max_cycles:
        _log(f"Max cycles reached ({cfg.max_cycles})")
        return "completed"

    # --- check-in ---
    if checkin_due(state.elapsed_seconds, cfg.checkin_minutes, state.last_checkin_hour):
        _log(f"Writing check-in (hour {state.last_checkin_hour + 1})")
        write_checkin(
            state, proof_dir, daemon_pid=os.getpid(),
            models_used=[cfg.main_model],
            selected_seeds=list(state.seeds_worked),
            active_seed=state.current_seed_id,
            seeds_completed=list(state.seeds_worked),
            seeds_skipped=list(state.seeds_skipped),
            science_modes_used=_SCIENCE_CYCLE,
            subagent_tasks_completed=len(pool.completed),
        )
        state.last_checkin_hour += 1
        state.checkin_count += 1

    # --- on-demand check-in ---
    if checkin_requested(cfg.state_dir):
        _log("On-demand check-in requested")
        write_checkin(
            state, proof_dir, daemon_pid=os.getpid(),
            models_used=[cfg.main_model],
            selected_seeds=list(state.seeds_worked),
            active_seed=state.current_seed_id,
            seeds_completed=list(state.seeds_worked),
            seeds_skipped=list(state.seeds_skipped),
            science_modes_used=_SCIENCE_CYCLE,
            subagent_tasks_completed=len(pool.completed),
            extra={"on_demand": True},
        )

    # --- checkpoint ---
    elapsed_min = int(state.elapsed_seconds // 60)
    cp_due = cfg.checkpoint_minutes > 0 and \
        (elapsed_min // cfg.checkpoint_minutes) > state.last_checkpoint_minute
    if cp_due:
        state.last_checkpoint_minute = elapsed_min // cfg.checkpoint_minutes
        state.checkpoint_count += 1
        _append_jsonl(proof_dir / "checkpoints.jsonl", [{
            "checkpoint": state.checkpoint_count,
            "elapsed": state.elapsed_seconds,
            "cycle": state.cycle_count,
            "time": now_str,
        }])

    # --- boundary scan ---
    bs_due = cfg.boundary_scan_minutes > 0 and \
        (elapsed_min // cfg.boundary_scan_minutes) > state.last_boundary_scan_minute
    if bs_due:
        state.last_boundary_scan_minute = elapsed_min // cfg.boundary_scan_minutes
        state.boundary_scan_count += 1
        _append_jsonl(proof_dir / "boundary_scans.jsonl", [{
            "scan": state.boundary_scan_count,
            "elapsed": state.elapsed_seconds,
            "violations": state.boundary_violations,
            "time": now_str,
            "result": "GREEN" if state.boundary_violations == 0 else "RED",
        }])

    # --- pick seed + autopilot ---
    seeds = build_research_seeds()
    seed_id = _pick_next_seed(state, seeds)
    if seed_id is None:
        _log("All seeds worked or skipped — cycling back to priority seeds")
        state.seeds_worked.clear()
        seed_id = _pick_next_seed(state, seeds)
        if seed_id is None:
            return "completed"

    seed = get_seed(seed_id)
    if seed is None:
        _log(f"Seed {seed_id} not found, skipping")
        state.seeds_skipped.append(seed_id)
        return "continue"

    state.current_seed_id = seed_id
    state.current_model = cfg.main_model

    # Autopilot: Zero proposes, runtime disposes
    sp = propose(proposal_kind="research_seed_selection", proposed_at=now_str,
                 research_seed_id=seed_id, reason="daemon scheduler selected seed")
    sd = dispose(sp, decided_at=now_str)
    mp = propose(proposal_kind="model_assignment", proposed_at=now_str,
                 model_id=cfg.main_model, requested_model_slot="main",
                 research_seed_id=seed_id, reason="main brain for seed")
    md = dispose(mp, decided_at=now_str)
    state.autopilot_proposals += 2
    state.autopilot_decisions += 2
    state.autopilot_approvals += 2

    _append_jsonl(proof_dir / "autopilot_proposals.jsonl", [sp, mp])
    _append_jsonl(proof_dir / "autopilot_decisions.jsonl", [sd, md])

    # --- run science modes on this seed with model-role routing ---
    available_models = getattr(cfg, "available_models", [])
    failure_tracker = getattr(state, "_failure_tracker", None)
    if failure_tracker is None:
        failure_tracker = SeedModeFailureTracker()
        state._failure_tracker = failure_tracker

    if failure_tracker.all_modes_failed(seed_id, _SCIENCE_CYCLE):
        _log(f"SKIP seed {seed_id}: all modes failed, marking YELLOW_SKIPPED_AFTER_FAILURES")
        _append_jsonl(proof_dir / "seed_skip_after_failures.jsonl", [{
            "seed_id": seed_id, "reason": "all_modes_failed_repeatedly",
            "failure_count": failure_tracker.seed_failure_count(seed_id),
            "time": now_str,
        }])
        state.seeds_skipped.append(seed_id)
        state.evidence_gaps += 1
        _append_jsonl(proof_dir / "evidence_gap_ledger.jsonl", [{
            "seed_id": seed_id, "gap": "skipped after repeated failures", "is_action": False,
        }])
        return "continue"

    triage_outputs = {}

    for mode in _SCIENCE_CYCLE:
        if panic_requested(cfg.state_dir):
            return "panic"
        if stop_requested(cfg.state_dir):
            return "stop"

        prompt_fn = _PROMPT.get(mode)
        if prompt_fn is None:
            continue

        role = resolve_subagent_role(mode)
        if role is None or not is_registered_subagent_role(role):
            _log(f"SKIP: no registered role for mode {mode}")
            _append_jsonl(proof_dir / "subagent_role_mapping_errors.jsonl", [{
                "mode": mode, "seed_id": seed_id, "resolved_role": role,
                "error": "no registered subagent role for science mode",
                "action": "skipped", "time": now_str,
            }])
            state.receipt_count += 1
            if state.verdict_so_far == "YELLOW_IN_PROGRESS":
                state.verdict_so_far = "YELLOW_RECOVERABLE_ERROR"
            continue

        route = route_task(mode, role, available_models)
        selected_model = route.selected_model_id or cfg.main_model
        role_policy = get_role_policy(route.model_role)

        if failure_tracker.should_skip(seed_id, mode, selected_model):
            _log(f"BACKOFF: {seed_id}/{mode}/{selected_model} failed repeatedly, skipping")
            _append_jsonl(proof_dir / "reasoning_exhaustion_backoff.jsonl", [{
                "seed_id": seed_id, "mode": mode, "model_id": selected_model,
                "action": "skipped_after_repeated_failure", "time": now_str,
            }])
            _append_jsonl(proof_dir / "evidence_gap_ledger.jsonl", [{
                "seed_id": seed_id, "gap": f"mode {mode} skipped: repeated failure backoff",
                "is_action": False,
            }])
            state.evidence_gaps += 1
            continue

        _append_jsonl(proof_dir / "model_route_decisions.jsonl", [asdict(route)])

        if route.gemma_tiny_prompt:
            prompt_text = gemma_tiny_prompt_for_mode(mode, seed.short_name or seed.seed_id)
        else:
            prompt_text = prompt_fn(seed)

        timeout_s = role_policy.preferred_timeout_seconds if role_policy else cfg.per_call_timeout_seconds
        max_tokens = role_policy.default_max_tokens if role_policy else cfg.max_tokens
        retry_tokens = role_policy.retry_max_tokens if role_policy else 192

        task = create_task(role=role, seed_id=seed_id, science_mode=mode)
        pool.enqueue(task)
        state.current_task_id = task.task_id
        state.current_model = selected_model

        _heartbeat()
        _log(f"Cycle {state.cycle_count}: {seed_id} / {mode} -> {selected_model} ({route.model_role})")

        try:
            primary, retry = infer_with_retry(
                base_url=cfg.lmstudio_base_url, model=selected_model,
                prompt=prompt_text, prompt_id=f"{seed_id}_{mode}",
                task_id=task.task_id, science_mode=mode, seed_id=seed_id,
                final_answer_retry=cfg.final_answer_retry,
                timeout_s=timeout_s,
                max_tokens=max_tokens,
            )
        except Exception as e:
            task.error = str(e)[:200]
            pool.finish(task, success=False)
            failure_tracker.record_failure(seed_id, mode, selected_model)
            _heartbeat()
            state.receipt_count += 1
            continue

        _heartbeat()

        cls = primary.classification
        if cls in state.output_classifications:
            state.output_classifications[cls] += 1
        task.classification = cls
        task.content_chars = primary.content_char_count
        task.reasoning_chars = primary.reasoning_char_count

        if retry is not None:
            state.retry_attempts += 1
            retry_cls = retry.classification
            task.retry_classification = retry_cls
            if retry_cls in state.output_classifications:
                state.output_classifications[retry_cls] += 1
            if retry_cls == "final_answer_retry_success":
                state.retry_successes += 1
            else:
                state.retry_failures += 1

        usable = cls in ("normal_content", "content_plus_reasoning", "truncated_content") \
            or (retry and retry.classification == "final_answer_retry_success")
        task.usable = usable
        pool.finish(task, success=usable)

        if not usable and cls in ("reasoning_only_truncated", "empty_content"):
            failure_tracker.record_failure(seed_id, mode, selected_model)
            _append_jsonl(proof_dir / "reasoning_exhaustion_backoff.jsonl", [{
                "seed_id": seed_id, "mode": mode, "model_id": selected_model,
                "classification": cls, "action": "recorded_failure_backoff",
                "time": now_str,
            }])
            _append_jsonl(proof_dir / "evidence_gap_ledger.jsonl", [{
                "seed_id": seed_id, "gap": f"mode {mode}: {cls} on {selected_model}",
                "is_action": False,
            }])
            state.evidence_gaps += 1
            if state.verdict_so_far == "YELLOW_IN_PROGRESS":
                state.verdict_so_far = "YELLOW_RECOVERABLE_ERROR"

        if usable and route.model_role in ("fast_triage", "fast_math_or_coder"):
            triage_outputs[mode] = (primary.content_char_count, task.task_id)

        recs = [primary]
        if retry:
            recs.append(retry)
        _append_jsonl(proof_dir / "live_local_reasoning_receipts.jsonl", recs)
        _append_jsonl(proof_dir / "subagent_task_receipts.jsonl", [task])
        state.receipt_count += len(recs) + 1

        psel = select_profiles_for_mode(task.task_id, mode)
        _append_jsonl(proof_dir / "profile_assignment_receipts.jsonl", [psel])

        _append_jsonl(proof_dir / "science_mode_assignments.jsonl", [{
            "seed_id": seed_id, "science_mode": mode,
            "promotion_allowed": False, "operator_review_required": True,
        }])

        if cls in ("forbidden_model_attempt", "remote_fallback_attempt"):
            state.boundary_violations += 1
            state.verdict_so_far = "RED_BOUNDARY_VIOLATION"
            _log(f"BOUNDARY VIOLATION: {cls}")

    # --- triage-then-synthesis: if triage outputs exist, Gemma synthesizes ---
    if triage_outputs and not panic_requested(cfg.state_dir) and not stop_requested(cfg.state_dir):
        triage_summary = "; ".join(f"{m}: {cc} chars" for m, (cc, _) in triage_outputs.items())
        linked_tasks = [tid for _, (_, tid) in triage_outputs.items()]
        _append_jsonl(proof_dir / "triage_then_synthesis.jsonl", [{
            "seed_id": seed_id, "triage_modes": list(triage_outputs.keys()),
            "linked_task_ids": linked_tasks, "triage_summary_chars": len(triage_summary),
            "synthesis_model": GEMMA_MODEL_ID, "time": now_str,
        }])

    # --- large model trial lane ---
    large_trial_attempted = getattr(state, "_large_trial_attempted", False)
    large_trial_failed_models = getattr(state, "_large_trial_failed_models", set())
    if (not large_trial_attempted and triage_outputs
            and not panic_requested(cfg.state_dir)
            and not stop_requested(cfg.state_dir)):
        from .large_model_trial import LARGE_TRIAL_CANDIDATES as _LT_CANDIDATES
        lt_tried = False
        for lt_candidate in _LT_CANDIDATES:
            if lt_candidate not in available_models:
                continue
            if lt_candidate in large_trial_failed_models:
                continue
            from hg_runtime.profile_model_autopilot.model_slots import is_forbidden as _is_forb, is_allowed as _is_alw
            if _is_forb(lt_candidate):
                continue
            allowed, _ = _is_alw(lt_candidate)
            if not allowed:
                continue
            pf = run_resource_preflight(lt_candidate, available_models)
            _append_jsonl(proof_dir / "large_model_resource_preflight.jsonl", [asdict(pf)])
            if not pf.resource_safe:
                _log(f"Large trial: {lt_candidate} resource unsafe, trying next")
                _append_jsonl(proof_dir / "large_model_trial_receipts.jsonl", [{
                    "action": "resource_skip", "candidate": lt_candidate,
                    "reason": pf.reason, "resource_safe": False,
                    "verdict": "YELLOW_LARGE_MODEL_RESOURCE_UNSAFE", "time": now_str,
                }])
                state.receipt_count += 1
                continue

            lt_task = build_large_trial_task(
                lt_candidate, seed_id, seed.short_name or seed.seed_id)
            _log(f"Large trial: {lt_candidate} on {seed_id}")
            _heartbeat()
            try:
                lt_primary, lt_retry = infer_with_retry(
                    base_url=cfg.lmstudio_base_url, model=lt_candidate,
                    prompt=lt_task.prompt, prompt_id=f"large_trial_{seed_id}",
                    task_id=lt_task.task_id, science_mode="adversarial_peer_review",
                    seed_id=seed_id, final_answer_retry=cfg.final_answer_retry,
                    timeout_s=240, max_tokens=768,
                )
                lt_task.content_char_count = lt_primary.content_char_count
                lt_task.reasoning_char_count = lt_primary.reasoning_char_count
                lt_task.finish_reason = lt_primary.finish_reason
                lt_task.classification = lt_primary.classification
                lt_task.usable = lt_primary.classification in (
                    "normal_content", "content_plus_reasoning", "truncated_content")
                if lt_retry and lt_retry.classification == "final_answer_retry_success":
                    lt_task.usable = True
                state._large_trial_attempted = True
            except Exception as e:
                lt_task.error = str(e)[:200]
                lt_task.usable = False
                large_trial_failed_models.add(lt_candidate)
                state._large_trial_failed_models = large_trial_failed_models

            triage_chars = sum(cc for cc, _ in triage_outputs.values())
            comp = evaluate_large_trial_result(lt_task, fast_triage_chars=triage_chars)
            _append_jsonl(proof_dir / "large_model_trial_receipts.jsonl", [asdict(lt_task)])
            _append_jsonl(proof_dir / "large_model_trial_comparison.jsonl", [asdict(comp)])
            _append_jsonl(proof_dir / "large_model_trial_operator_review.jsonl", [{
                "task_id": lt_task.task_id, "candidate": lt_candidate,
                "usable": lt_task.usable, "operator_review_required": True,
                "recommendation_promote": False, "time": now_str,
            }])
            state.receipt_count += 3
            _heartbeat()
            lt_tried = True
            break

        if not lt_tried:
            _append_jsonl(proof_dir / "large_model_trial_receipts.jsonl", [{
                "action": "skipped", "reason": "no eligible resource-safe large candidate",
                "time": now_str,
            }])
            state.receipt_count += 1

    # Falsification targets
    ftargets = build_falsification_targets(seed_id, seed.seed_text, seed.domain_tags)
    _append_jsonl(proof_dir / "falsification_targets.jsonl", ftargets)

    # Seed progress + ledgers
    _append_jsonl(proof_dir / "research_seed_progress.jsonl", [{
        "seed_id": seed_id, "modes": _SCIENCE_CYCLE, "status": "worked_live_local",
        "time": now_str,
    }])
    _append_jsonl(proof_dir / "evidence_gap_ledger.jsonl", [{
        "seed_id": seed_id, "gap": "evidence not gathered", "is_action": False,
    }])
    _append_jsonl(proof_dir / "uncertainty_ledger.jsonl", [{
        "seed_id": seed_id, "uncertainty": "preserved", "promotion_allowed": False,
    }])
    _append_jsonl(proof_dir / "knowledge_candidate_ledger.jsonl", [{
        "seed_id": seed_id, "classification": "candidate knowledge pending review",
        "promoted": False,
    }])
    state.evidence_gaps += 1
    state.uncertainty_records += 1
    state.knowledge_candidates += 1

    state.seeds_worked.append(seed_id)
    state.cycle_count += 1

    # Post-cycle STOP/PANIC check
    if panic_requested(cfg.state_dir):
        return "panic"
    if stop_requested(cfg.state_dir):
        return "stop"

    save_state(state, cfg.state_dir)
    return "continue"
