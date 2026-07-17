"""EXCITON Phase 2 — soak watchtower data from real run logs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.social_capability.review_policy import unreviewed_publish_path
from hg_runtime.social_capability.review_queue import is_publish_paused, queue_summary, review_queue_visible
from hg_runtime.bounded_soak.active_run import (
    assess_active_run,
    active_soak_run_dir as _active_from_bounded,
    event_timestamp,
    observer_event_lines,
    soak_event_lines,
)

WORKSPACE = Path(__file__).resolve().parents[2]
SOAK_ROOT = WORKSPACE / ".hg-local" / "soak"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _parse_lines(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def active_soak_run_dir() -> Path | None:
    return _active_from_bounded(WORKSPACE)


def _observation_ready(run_dir: Path, intent: dict[str, Any], elapsed_min: float) -> bool:
    obs = int(intent.get("observation_minutes", 30))
    if elapsed_min < obs:
        return False
    for name in (
        "checkpoint_observation-30m.json",
        "checkpoint_observation-30m-pre-flip.json",
        "checkpoint_observation-ready.json",
    ):
        cp = run_dir / name
        if cp.is_file():
            data = _read_json(cp) or {}
            if str(data.get("verdict", "")).startswith("GREEN"):
                return True
    return elapsed_min >= obs


def _operator_confirmed(control: dict[str, Any], run_dir: Path) -> bool:
    if control.get("operator_confirmed_after_observation"):
        return True
    if control.get("operator_approved_after_observation") and (
        run_dir / "operator_publish_confirmation.json"
    ).is_file():
        return True
    receipt = _read_json(run_dir / "operator_publish_confirmation.json")
    return bool(receipt and receipt.get("confirmed"))


def build_soak_watchtower(*, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or WORKSPACE
    run_dir = active_soak_run_dir()
    if not run_dir:
        return {
            "active": False,
            "verdict": "GREEN_SOAK_IDLE",
            "observer_verdict": "IDLE",
            "data_tier": "LIVE",
        }

    intent = _read_json(run_dir / "operator_intent.json") or {}
    control = _read_json(run_dir / "run_control.json") or {}
    commands = soak_event_lines(run_dir)
    observer = observer_event_lines(run_dir)
    soak_receipts = _parse_lines(run_dir / "soak_receipts.jsonl")
    social_receipts = _parse_lines(run_dir / "social_receipts.jsonl")
    draft_only_mode = bool(
        control.get("draft_only_mode")
        or intent.get("profile") == "overnight-draft-only"
        or intent.get("approval_mode") == "MORNING_REVIEW_REQUIRED"
    )

    started: str | None = None
    run_id: str | None = None
    for ev in commands:
        if ev.get("event") == "SOAK_START":
            started = event_timestamp(ev)
            run_id = ev.get("run_id") or (ev.get("detail") or {}).get("run_id")
            break

    elapsed_min = 0.0
    remaining_min = float(intent.get("duration_minutes", 360))
    if started:
        try:
            t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
            elapsed_min = round((datetime.now(timezone.utc) - t0).total_seconds() / 60.0, 1)
            remaining_min = max(0.0, float(intent.get("duration_minutes", 360)) - elapsed_min)
        except ValueError:
            pass

    obs_min = int(intent.get("observation_minutes", 30))
    cycle_s = int(intent.get("cycle_seconds") or intent.get("cycle_interval_seconds") or 600)
    last_cycle = next((e for e in reversed(commands) if e.get("event") == "CYCLE_COMPLETE"), None)
    next_cycle_eta_s: int | None = None
    last_cycle_ts = event_timestamp(last_cycle) if last_cycle else None
    if last_cycle_ts:
        try:
            t_last = datetime.fromisoformat(str(last_cycle_ts).replace("Z", "+00:00"))
            delta = (datetime.now(timezone.utc) - t_last).total_seconds()
            next_cycle_eta_s = max(0, int(cycle_s - delta))
        except ValueError:
            next_cycle_eta_s = cycle_s

    observer_verdict = "UNKNOWN"
    observer_heartbeat_age_s: float | None = None
    if observer:
        last = observer[-1]
        observer_verdict = str(last.get("verdict", "GREEN_OBSERVER"))
        obs_ts = event_timestamp(last)
        if obs_ts:
            try:
                t_obs = datetime.fromisoformat(str(obs_ts).replace("Z", "+00:00"))
                observer_heartbeat_age_s = round(
                    (datetime.now(timezone.utc) - t_obs).total_seconds(), 1
                )
            except ValueError:
                pass

    forbidden: list[str] = []
    credential_leaks = 0
    for line in soak_receipts + social_receipts + observer:
        detail = json.dumps(line).lower()
        if "dm_" in detail or '"dm"' in detail:
            forbidden.append("dm_attempt")
        if "credential_exposed" in detail and "false" not in detail:
            credential_leaks += 1
            forbidden.append("credential_exposed")

    publish_enabled = bool(control.get("allow_live_social_publish", False))
    operator_confirmed = _operator_confirmed(control, run_dir)
    observation_ready = _observation_ready(run_dir, intent, elapsed_min)
    in_observation = elapsed_min < obs_min

    posts_published = sum(
        1 for r in soak_receipts if "PUBLISHED" in json.dumps(r).upper()
    )
    posts_attempted = sum(
        1 for r in social_receipts + soak_receipts if "publish" in json.dumps(r).lower()
    )

    auto_flip_detected = any(e.get("event") == "AUTO_PUBLISH_FLIP" for e in commands)
    phase = "draft_only" if draft_only_mode and not publish_enabled else (
        "observation" if in_observation else (
            "awaiting_operator_confirm" if observation_ready and not operator_confirmed else "publish_enabled" if publish_enabled else "post_observation"
        )
    )

    panic = (ws / ".hg-local/soak/PANIC").exists()
    stop = (ws / ".hg-local/soak/STOP").exists()

    review_stats = {
        "review_queue_visible": False,
        "queued_item_count": 0,
        "approved_item_count": 0,
        "denied_item_count": 0,
        "live_publish_paused_for_review": bool(control.get("live_publish_paused_for_review", False)),
        "approved_only_mode": bool(control.get("approved_only_mode", False)),
        "unreviewed_publish_path": False,
        "legacy_incident_recorded": False,
    }
    if review_queue_visible(run_dir):
        summary = queue_summary(run_dir)
        counts = summary.get("counts", {})
        review_stats.update({
            "review_queue_visible": True,
            "queued_item_count": counts.get("queued", 0),
            "approved_item_count": counts.get("approved", 0),
            "denied_item_count": counts.get("denied", 0),
            "live_publish_paused_for_review": summary.get("live_publish_paused", False),
            "approved_only_mode": summary.get("approved_only_mode", False),
            "legacy_incident_recorded": summary.get("legacy_incident_recorded", False),
        })
    review_stats["unreviewed_publish_path"] = unreviewed_publish_path(
        publish_enabled=publish_enabled,
        live_publish_paused=review_stats["live_publish_paused_for_review"] or is_publish_paused(run_dir),
        approved_only_mode=review_stats["approved_only_mode"],
    )

    active_assessment = assess_active_run(run_dir=run_dir)
    finalization_state = "FINALIZED" if (run_dir / "final_summary.json").is_file() else (
        "RUNNING" if active_assessment.get("active") else "ENDED_NOT_FINALIZED"
    )
    safety_verdict = active_assessment.get("verdict", "GREEN_ACTIVE_RUN_SAFE")
    # A finalized (or otherwise not-active) run's publish flag is historical, not a live risk.
    # Only an *active* run can breach the publish-without-observer / stale-observer invariants.
    run_is_live = bool(active_assessment.get("active")) and finalization_state != "FINALIZED"
    if run_is_live and publish_enabled and not observer:
        safety_verdict = "RED_ACTIVE_RUN_PUBLISH_ENABLED_WITHOUT_OBSERVER"
    elif run_is_live and publish_enabled and observer_heartbeat_age_s and observer_heartbeat_age_s > 180:
        safety_verdict = "RED_OBSERVER_STALE_WHILE_PUBLISH_ENABLED"

    return {
        "active": True,
        "data_tier": "LIVE",
        "run_id": run_id or run_dir.name,
        "run_dir": str(run_dir.relative_to(ws)),
        "started_at": started,
        "duration_minutes": intent.get("duration_minutes", 360),
        "observation_minutes": obs_min,
        "elapsed_minutes": elapsed_min,
        "remaining_minutes": round(remaining_min, 1),
        "current_phase": phase,
        "in_observation_window": in_observation,
        "observation_ready_for_confirmation": observation_ready and not operator_confirmed,
        "observation_checkpoint_verdict": (
            "GREEN_OBSERVATION_READY_FOR_OPERATOR_CONFIRMATION"
            if observation_ready and not operator_confirmed
            else ("GREEN_OBSERVATION_COMPLETE" if observation_ready else "YELLOW_OBSERVATION_IN_PROGRESS")
        ),
        "publish_enabled": publish_enabled,
        "operator_confirmed_after_observation": operator_confirmed,
        "operator_confirmation_required": (
            observation_ready and not operator_confirmed and publish_enabled and not draft_only_mode
        ),
        "draft_only_mode": draft_only_mode,
        "max_posts": int(control.get("max_posts_total", intent.get("max_posts_total", 0))),
        "posts_attempted": posts_attempted,
        "posts_published": posts_published,
        "current_cycle": sum(1 for e in commands if e.get("event") == "CYCLE_COMPLETE"),
        "next_cycle_eta_seconds": next_cycle_eta_s,
        "latest_cycle_receipt": (last_cycle or {}).get("detail"),
        "observer_verdict": observer_verdict,
        "observer_heartbeat_age_seconds": observer_heartbeat_age_s,
        "forbidden_action_count": len(set(forbidden)),
        "credential_leak_count": credential_leaks,
        "stop_file_present": stop,
        "panic_file_present": panic,
        "stop_available": True,
        "panic_available": True,
        "auto_publish_flip_detected": auto_flip_detected,
        "command_events": [str(e.get("event")) for e in commands[-12:]],
        "finalization_state": finalization_state,
        "active_run_verdict": safety_verdict,
        "observer_attached": bool(observer),
        "requires_operator_decision": active_assessment.get("requires_operator_action", False),
        "tasks_logged": _count_jsonl(run_dir / "soak_receipts.jsonl"),
        **review_stats,
        "authority_created": False,
        "permission_granted": False,
        "advisory_only": True,
    }


def soak_run_status() -> dict[str, Any]:
    """Backward-compatible summary for Phase 1 panels."""
    wt = build_soak_watchtower()
    if not wt.get("active"):
        return {"active": False}
    return {
        "active": True,
        "run_dir": wt["run_dir"],
        "duration_minutes": wt["duration_minutes"],
        "observation_minutes": wt["observation_minutes"],
        "elapsed_minutes": wt["elapsed_minutes"],
        "remaining_minutes": wt.get("remaining_minutes", 0),
        "publish_enabled": wt["publish_enabled"],
        "operator_confirmed": wt["operator_confirmed_after_observation"],
        "operator_confirmation_required": wt["operator_confirmation_required"],
        "max_posts": wt["max_posts"],
        "command_events": wt.get("command_events", []),
        "tasks_logged": wt["tasks_logged"],
        "observer_verdict": wt["observer_verdict"],
        "observer_heartbeat_age_seconds": wt.get("observer_heartbeat_age_seconds"),
        "current_phase": wt["current_phase"],
        "next_cycle_eta_seconds": wt.get("next_cycle_eta_seconds"),
    }


__all__ = ["active_soak_run_dir", "build_soak_watchtower", "soak_run_status"]
