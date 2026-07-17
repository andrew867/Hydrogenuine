"""Overnight bounded social soak — long-running governed loop."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from hg_runtime.bounded_soak.budget import BudgetTracker
from hg_runtime.bounded_soak.receipts import ewj_soak_event, write_soak_receipt
from hg_runtime.bounded_soak.active_run import can_publish_on_active_run
from hg_runtime.bounded_soak.supervisor_lock import acquire_supervisor_lock, heartbeat_supervisor_lock
from hg_runtime.bounded_soak.schema import (
    BoundedSoakProfile,
    SoakBudget,
    SoakReceipt,
    SoakTaskResult,
    SoakVerdict,
    new_id,
)
from hg_runtime.bounded_soak.stop_conditions import check_stop
from hg_runtime.bounded_soak.supervisor import _run_task
from hg_runtime.social_capability.publish_permit import PublishPolicy
from hg_runtime.social_capability.review_queue import approved_only_mode, is_publish_paused

WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass
class OvernightSoakConfig:
    run_dir: Path
    profile: BoundedSoakProfile
    observation_minutes: int = 30
    cycle_interval_seconds: int = 600
    panic_file: Path | None = None
    stop_file: Path | None = None
    on_observation_complete: Callable[[], None] | None = None
    command_log: Path | None = None
    soak_receipts_log: Path | None = None


def _log(path: Path | None, event: str, detail: dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "detail": detail,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, sort_keys=True) + "\n")


def _load_run_control(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "run_control.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _effective_profile(base: BoundedSoakProfile, run_dir: Path, elapsed_min: float) -> BoundedSoakProfile:
    control = _load_run_control(run_dir)
    publish = bool(control.get("allow_live_social_publish", base.allow_live_social_publish))
    confirmed = bool(
        control.get("operator_confirmed_after_observation")
        or (run_dir / "operator_publish_confirmation.json").is_file()
    )
    paused = bool(control.get("live_publish_paused_for_review", False))
    approved_only = bool(control.get("approved_only_mode", False))
    if paused:
        publish = False
    elif approved_only:
        publish = bool(control.get("allow_live_social_publish", False)) and confirmed
    elif publish and not confirmed:
        publish = False
    max_posts = int(control.get("max_posts_total", base.max_posts))
    return BoundedSoakProfile(
        profile_id=base.profile_id,
        duration_minutes=base.duration_minutes,
        allow_live_social_read=base.allow_live_social_read,
        allow_live_social_publish=publish,
        max_posts=max_posts,
        operator_approval_required=base.operator_approval_required,
        tool_dry_run=base.tool_dry_run,
    )


def run_overnight_soak(config: OvernightSoakConfig) -> SoakReceipt:
    started = datetime.now(timezone.utc)
    run_id = new_id("overnight")
    budget = SoakBudget(
        max_duration_minutes=config.profile.duration_minutes,
        hard_max_minutes=config.profile.duration_minutes,
        max_posts=config.profile.max_posts or 3,
        max_tasks=500,
    )
    tracker = BudgetTracker(budget, started)
    ewj_start = ewj_soak_event(run_id, "start")
    ok_lock, lock_reason, _ = acquire_supervisor_lock(
        config.run_dir, supervisor_id=run_id, workspace=WORKSPACE
    )
    if not ok_lock:
        raise RuntimeError(lock_reason)
    _log(config.command_log, "SOAK_START", {"run_id": run_id, "profile": config.profile.to_payload()})

    results: list[SoakTaskResult] = []
    verdict = SoakVerdict.COMPLETE
    stop_reason: str | None = None
    observation_flipped = False
    last_post_at: float | None = None
    min_between = int(os.environ.get("HG_SOCIAL_MIN_SECONDS_BETWEEN_POSTS", "5400"))

    while True:
        should_stop, cond, reason = check_stop(
            tracker, panic_file=config.panic_file, stop_file=config.stop_file
        )
        if should_stop:
            verdict = SoakVerdict.PANIC if cond and cond.value == "panic_file" else SoakVerdict.STOPPED
            stop_reason = reason
            break
        if tracker.duration_exceeded():
            stop_reason = "duration budget reached"
            break

        elapsed_min = (datetime.now(timezone.utc) - started).total_seconds() / 60.0
        if not observation_flipped and elapsed_min >= config.observation_minutes:
            if config.on_observation_complete:
                config.on_observation_complete()
            observation_flipped = True
            _log(config.command_log, "SOAK_PHASE_RESTART", {
                "reason": "observation_complete_awaiting_operator_confirm",
                "elapsed_min": elapsed_min,
            })

        profile = _effective_profile(config.profile, config.run_dir, elapsed_min)
        cycle_tasks = ["status_check", "social_read_check", "curated_queue"]
        paused = is_publish_paused(config.run_dir)
        a_only = approved_only_mode(config.run_dir)
        if (
            not paused
            and a_only
            and profile.allow_live_social_publish
            and profile.max_posts > 0
        ):
            can_pub, pub_reason = can_publish_on_active_run()
            if can_pub and tracker.posts_used < profile.max_posts:
                if last_post_at is None or (time.monotonic() - last_post_at) >= min_between:
                    cycle_tasks.append("curated_publish")
            elif not can_pub:
                _log(config.command_log, "PUBLISH_BLOCKED", {"reason": pub_reason})

        heartbeat_supervisor_lock(config.run_dir, supervisor_id=run_id)

        for kind in cycle_tasks:
            res = _run_task(kind, profile, tracker, run_dir=config.run_dir)
            results.append(res)
            tracker.record_task()
            _log(config.soak_receipts_log, "TASK", res.to_payload())
            if "decision=PUBLISHED" in res.detail:
                last_post_at = time.monotonic()

        _log(config.command_log, "CYCLE_COMPLETE", {
            "elapsed_min": round(elapsed_min, 2),
            "posts_used": tracker.posts_used,
            "publish_enabled": profile.allow_live_social_publish,
        })
        time.sleep(config.cycle_interval_seconds)

    results.append(_run_task("final_summary", _effective_profile(config.profile, config.run_dir, 0), tracker))
    summary = (
        f"Overnight soak {run_id}: {verdict.value}. Cycles={len(results)}. "
        f"Posts={tracker.posts_used}. Stop={stop_reason or 'complete'}."
    )
    receipt = SoakReceipt(
        receipt_id=new_id("srec"),
        run_id=run_id,
        verdict=verdict,
        stop_reason=stop_reason,
        summary=summary,
        task_results=results[-50:],
        created_at=datetime.now(timezone.utc).isoformat(),
        ewj_start_ref=ewj_start,
        ewj_complete_ref=ewj_soak_event(run_id, "complete"),
    )
    config.run_dir.mkdir(parents=True, exist_ok=True)
    (config.run_dir / f"{run_id}.json").write_text(json.dumps(receipt.to_payload(), indent=2), encoding="utf-8")
    write_soak_receipt(receipt)
    _log(config.command_log, "SOAK_COMPLETE", {"verdict": verdict.value, "summary": summary[:500]})
    return receipt


__all__ = ["OvernightSoakConfig", "run_overnight_soak"]
