"""Hourly check-in writer — wall-clock based, never fabricated."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from .state import RunState


def checkin_due(elapsed_seconds: float, checkin_minutes: int,
                last_checkin_hour: int) -> bool:
    if checkin_minutes <= 0:
        return False
    expected = int(elapsed_seconds // (checkin_minutes * 60))
    return expected > last_checkin_hour


def write_checkin(state: RunState, proof_dir: str | Path, *,
                  daemon_pid: int, lmstudio_status: str = "reachable",
                  active_model_slots: list[str] | None = None,
                  models_used: list[str] | None = None,
                  selected_seeds: list[str] | None = None,
                  active_seed: str = "",
                  seeds_completed: list[str] | None = None,
                  seeds_skipped: list[str] | None = None,
                  active_profiles: list[str] | None = None,
                  subagent_tasks_completed: int = 0,
                  science_modes_used: list[str] | None = None,
                  source_count: int = 0,
                  forbidden_model_attempts: int = 0,
                  self_authorization_attempts: int = 0,
                  live_effect_attempts: int = 0,
                  public_claim_checker_hits: int = 0,
                  resource_notes: str = "",
                  next_planned_cycle: str = "",
                  operator_attention_required: bool = False,
                  extra: dict | None = None) -> tuple[Path, Path]:
    proof = Path(proof_dir)
    hour_n = state.last_checkin_hour + 1
    hour_label = f"hour_{hour_n:02d}"

    checkin = {
        "hour": hour_n,
        "label": hour_label,
        "wall_clock_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": state.elapsed_seconds,
        "daemon_pid": daemon_pid,
        "heartbeat_age_note": "fresh (just written)",
        "cycle_count": state.cycle_count,
        "current_verdict_so_far": state.verdict_so_far,
        "lmstudio_status": lmstudio_status,
        "active_model_slots": active_model_slots or [],
        "models_used": models_used or [],
        "selected_seeds": selected_seeds or [],
        "active_seed": active_seed,
        "seeds_completed": seeds_completed or [],
        "seeds_skipped": seeds_skipped or [],
        "active_profiles": active_profiles or [],
        "subagent_tasks_completed": subagent_tasks_completed,
        "science_modes_used": science_modes_used or [],
        "autopilot_proposals_count": state.autopilot_proposals,
        "autopilot_decisions_count": state.autopilot_decisions,
        "approvals": state.autopilot_approvals,
        "denials": state.autopilot_denials,
        "modifications": 0,
        "evidence_gaps_count": state.evidence_gaps,
        "uncertainty_records_count": state.uncertainty_records,
        "source_count": source_count,
        "knowledge_candidates_count": state.knowledge_candidates,
        "knowledge_promotions_count": state.knowledge_promotions,
        "checkpoint_count": state.checkpoint_count,
        "stop_panic_check_count": state.boundary_scan_count,
        "boundary_scan_count": state.boundary_scan_count,
        "receipt_gaps": 0,
        "output_classifications": state.output_classifications,
        "final_answer_retry_attempts": state.retry_attempts,
        "final_answer_retry_successes": state.retry_successes,
        "final_answer_retry_failures": state.retry_failures,
        "forbidden_model_attempts": forbidden_model_attempts,
        "self_authorization_attempts": self_authorization_attempts,
        "live_effect_attempts": live_effect_attempts,
        "public_claim_checker_hits": public_claim_checker_hits,
        "resource_notes": resource_notes,
        "next_planned_cycle": next_planned_cycle,
        "operator_attention_required": operator_attention_required,
    }
    if extra:
        checkin.update(extra)

    # Write JSONL line
    jsonl_path = proof / "hourly_checkins.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(checkin, default=str) + "\n")

    # Write hour_NN.md
    md_dir = proof / "hourly_checkins"
    md_dir.mkdir(parents=True, exist_ok=True)
    md_path = md_dir / f"{hour_label}.md"
    lines = [
        f"# {hour_label} — Check-in",
        f"",
        f"**Time:** {checkin['wall_clock_time']}",
        f"**Elapsed:** {state.elapsed_seconds:.0f}s ({state.elapsed_seconds/3600:.2f}h)",
        f"**Cycles:** {state.cycle_count}",
        f"**Verdict so far:** {state.verdict_so_far}",
        f"**Daemon PID:** {daemon_pid}",
        f"",
        f"## Output Classifications",
        f"",
    ]
    for cls, cnt in state.output_classifications.items():
        if cnt > 0:
            lines.append(f"- {cls}: {cnt}")
    lines += [
        f"",
        f"## Research Seeds",
        f"- Selected: {len(selected_seeds or [])}",
        f"- Active: {active_seed}",
        f"- Completed: {len(seeds_completed or [])}",
        f"- Skipped: {len(seeds_skipped or [])}",
        f"",
        f"## Retry Stats",
        f"- Attempts: {state.retry_attempts}",
        f"- Successes: {state.retry_successes}",
        f"- Failures: {state.retry_failures}",
        f"",
        f"## Boundaries",
        f"- Violations: {state.boundary_violations}",
        f"- Forbidden model attempts: {forbidden_model_attempts}",
        f"- Self-auth attempts: {self_authorization_attempts}",
        f"- Live effect attempts: {live_effect_attempts}",
        f"",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return jsonl_path, md_path


def future_checkin_is_fabricated(hour_n: int, elapsed_seconds: float,
                                 checkin_minutes: int) -> bool:
    min_elapsed = hour_n * checkin_minutes * 60
    return elapsed_seconds < min_elapsed
