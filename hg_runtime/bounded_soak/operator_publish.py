"""Operator-confirmed publish enable after observation checkpoint."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def observation_checkpoint_ready(run_dir: Path) -> tuple[bool, str]:
    """True when observation window elapsed and checkpoint is GREEN-ready."""
    intent = _read_json(run_dir / "operator_intent.json") or {}
    control = _read_json(run_dir / "run_control.json") or {}
    obs_min = int(intent.get("observation_minutes", 30))

    for name in run_dir.glob("checkpoint_*.json"):
        data = _read_json(name) or {}
        v = str(data.get("verdict", ""))
        if "OBSERVATION_READY" in v or name.name in (
            "checkpoint_observation-30m.json",
            "checkpoint_observation-ready.json",
        ):
            if v.startswith("GREEN"):
                return True, v
    # Fallback: explicit ready checkpoint
    ready = run_dir / "checkpoint_observation-ready.json"
    if ready.is_file():
        data = _read_json(ready) or {}
        return data.get("verdict", "").startswith("GREEN"), str(data.get("verdict", ""))

    # elapsed from SOAK_START in command log
    started = None
    log = run_dir / "command_log.jsonl"
    if log.is_file():
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("event") == "SOAK_START":
                started = ev.get("ts")
                break
    if not started:
        return False, "YELLOW_OBSERVATION_START_UNKNOWN"
    try:
        t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - t0).total_seconds() / 60.0
    except ValueError:
        return False, "YELLOW_OBSERVATION_TIME_PARSE"
    if elapsed < obs_min:
        return False, "YELLOW_OBSERVATION_IN_PROGRESS"
    if control.get("operator_confirmed_after_observation"):
        return True, "GREEN_OBSERVATION_ALREADY_CONFIRMED"
    return True, "GREEN_OBSERVATION_READY_FOR_OPERATOR_CONFIRMATION"


def operator_confirmed(run_dir: Path) -> bool:
    receipt = _read_json(run_dir / "operator_publish_confirmation.json")
    if receipt and receipt.get("confirmed"):
        return True
    control = _read_json(run_dir / "run_control.json") or {}
    return bool(control.get("operator_confirmed_after_observation"))


def stop_or_panic_active(workspace: Path | None = None) -> bool:
    ws = workspace or WORKSPACE
    return (ws / ".hg-local/soak/STOP").exists() or (ws / ".hg-local/soak/PANIC").exists()


def write_operator_confirmation(
    run_dir: Path,
    *,
    max_posts: int,
    min_seconds_between_posts: int,
    operator_note: str = "",
) -> dict[str, Any]:
    ready, verdict = observation_checkpoint_ready(run_dir)
    if not ready and not verdict.startswith("GREEN_OBSERVATION_READY"):
        raise ValueError(f"observation not ready: {verdict}")
    if stop_or_panic_active():
        raise ValueError("stop or panic active; cannot confirm publish")
    if operator_confirmed(run_dir):
        raise ValueError("already confirmed for this run")

    receipt = {
        "schema": "operator-publish-confirmation",
        "confirmed": True,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "allow_live_social_publish": True,
        "max_posts": max_posts,
        "min_seconds_between_posts": min_seconds_between_posts,
        "operator_approved_after_observation": True,
        "operator_note": operator_note[:500] if operator_note else "",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "operator_publish_confirmation.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    control = _read_json(run_dir / "run_control.json") or {}
    control.update({
        "allow_live_social_publish": True,
        "max_posts_total": max_posts,
        "min_seconds_between_posts": min_seconds_between_posts,
        "operator_confirmed_after_observation": True,
        "operator_approved_after_observation": True,
        "updated_at": receipt["confirmed_at"],
    })
    (run_dir / "run_control.json").write_text(json.dumps(control, indent=2) + "\n", encoding="utf-8")
    return receipt


__all__ = [
    "observation_checkpoint_ready",
    "operator_confirmed",
    "stop_or_panic_active",
    "write_operator_confirmation",
]
