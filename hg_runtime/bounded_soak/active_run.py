"""Active soak run assessment — explicit operator decisions, no silent publish."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.bounded_soak.stop_panic_runtime import stop_panic_state

WORKSPACE = Path(__file__).resolve().parents[2]
SOAK_ROOT = WORKSPACE / ".hg-local" / "soak"
OBSERVER_STALE_SECONDS = 180


def active_soak_run_dir(workspace: Path | None = None) -> Path | None:
    ws = workspace or WORKSPACE
    pointer = ws / ".hg-local" / "soak" / "current_run.txt"
    if pointer.is_file():
        raw = pointer.read_text(encoding="utf-8").strip()
        if raw:
            p = Path(raw)
            if not p.is_absolute():
                p = ws / p
            if p.is_dir():
                return p
    runs = ws / ".hg-local" / "soak" / "runs"
    if not runs.is_dir():
        return None
    for d in sorted(runs.iterdir(), reverse=True):
        if d.is_dir() and (
            (d / "command_log.jsonl").exists() or (d / "event_log.jsonl").exists()
        ):
            return d
    return None


def _parse_jsonl(path: Path) -> list[dict[str, Any]]:
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


def soak_event_lines(run_dir: Path) -> list[dict[str, Any]]:
    """Command + event logs (legacy supervised soak and overnight draft soak)."""
    out: list[dict[str, Any]] = []
    for name in ("command_log.jsonl", "event_log.jsonl"):
        out.extend(_parse_jsonl(run_dir / name))
    return out


def observer_event_lines(run_dir: Path) -> list[dict[str, Any]]:
    for name in ("observer_log.jsonl", "observer.jsonl"):
        lines = _parse_jsonl(run_dir / name)
        if lines:
            return lines
    return []


def event_timestamp(ev: dict[str, Any]) -> str | None:
    ts = ev.get("ts") or ev.get("timestamp")
    return str(ts) if ts else None


class ActiveRunDecision(str, Enum):
    PAUSE_PUBLISH = "pause_publish"
    STOP_RUN = "stop_run"
    CONTINUE_APPROVED_ONLY_WITH_OBSERVER = "continue_approved_only_with_observer"
    FINALIZE_ENDED_RUN = "finalize_ended_run"
    READ_DRAFT_ONLY = "read_draft_only"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _run_is_active(run_dir: Path) -> bool:
    summary = _read_json(run_dir / "final_summary.json")
    if summary and summary.get("finalized_at"):
        return False
    if not soak_event_lines(run_dir):
        return False
    has_start = False
    has_complete = False
    for ev in soak_event_lines(run_dir):
        if ev.get("event") == "SOAK_START":
            has_start = True
        if ev.get("event") in ("SOAK_COMPLETE", "SOAK_STOPPED", "SOAK_FINALIZED"):
            has_complete = True
    return has_start and not has_complete


def _observer_fresh(run_dir: Path) -> tuple[bool, float | None]:
    lines = observer_event_lines(run_dir)
    if not lines:
        return False, None
    last = lines[-1]
    ts = event_timestamp(last)
    if not ts:
        return False, None
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - t).total_seconds()
        return age <= OBSERVER_STALE_SECONDS, age
    except ValueError:
        return False, None


def assess_active_run(*, workspace: Path | None = None, run_dir: Path | None = None) -> dict[str, Any]:
    ws = workspace or WORKSPACE
    rd = run_dir or active_soak_run_dir()
    sp = stop_panic_state(ws)

    if not rd:
        return {
            "active": False,
            "verdict": "GREEN_ACTIVE_RUN_SAFE",
            "human_message": "No active soak run.",
            "available_decisions": [],
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }

    active = _run_is_active(rd)
    control = _read_json(rd / "run_control.json") or {}
    publish_enabled = bool(control.get("allow_live_social_publish", False))
    observer_ok, observer_age = _observer_fresh(rd)
    finalized = _read_json(rd / "final_summary.json") is not None

    available: list[str] = []
    if not active and not finalized:
        available.append(ActiveRunDecision.FINALIZE_ENDED_RUN.value)
    if active:
        available.extend([
            ActiveRunDecision.PAUSE_PUBLISH.value,
            ActiveRunDecision.STOP_RUN.value,
            ActiveRunDecision.READ_DRAFT_ONLY.value,
        ])
        if observer_ok:
            available.append(ActiveRunDecision.CONTINUE_APPROVED_ONLY_WITH_OBSERVER.value)

    verdict = "GREEN_ACTIVE_RUN_SAFE"
    if sp.panic_active:
        verdict = "RED_ACTIVE_RUN_PUBLISH_ENABLED_WITHOUT_OBSERVER"
    elif active and publish_enabled and not observer_ok:
        verdict = "RED_ACTIVE_RUN_PUBLISH_ENABLED_WITHOUT_OBSERVER"
    elif active and publish_enabled:
        verdict = "YELLOW_ACTIVE_RUN_OPERATOR_DECISION_REQUIRED"
    elif not active and not finalized:
        verdict = "YELLOW_RUN_ENDED_NOT_FINALIZED"

    return {
        "active": active,
        "run_dir": str(rd),
        "publish_enabled": publish_enabled,
        "observer_attached": observer_ok,
        "observer_heartbeat_age_seconds": observer_age,
        "finalized": finalized,
        "stop_active": sp.stop_active,
        "panic_active": sp.panic_active,
        "verdict": verdict,
        "human_message": _human_for_verdict(verdict),
        "available_decisions": available,
        "requires_operator_action": verdict.startswith("RED") or verdict.startswith("YELLOW"),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def _human_for_verdict(verdict: str) -> str:
    mapping = {
        "GREEN_ACTIVE_RUN_SAFE": "Active run is safe or no run active.",
        "YELLOW_ACTIVE_RUN_OPERATOR_DECISION_REQUIRED": "Publish enabled — operator must choose pause, stop, or continue with observer.",
        "RED_ACTIVE_RUN_PUBLISH_ENABLED_WITHOUT_OBSERVER": "Publish enabled without a fresh observer — pause publish immediately.",
        "YELLOW_RUN_ENDED_NOT_FINALIZED": "Run ended but not finalized — operator must finalize with proof.",
    }
    return mapping.get(verdict, verdict)


def apply_active_run_decision(
    decision: str,
    *,
    run_dir: Path,
    workspace: Path | None = None,
    operator_ref: str = "local-operator",
) -> dict[str, Any]:
    ws = workspace or WORKSPACE
    d = decision.lower()
    assessment = assess_active_run(workspace=ws, run_dir=run_dir)
    if d not in assessment.get("available_decisions", []):
        if d == ActiveRunDecision.FINALIZE_ENDED_RUN.value and not assessment["active"]:
            pass
        elif d not in {x.value for x in ActiveRunDecision}:
            return {"ok": False, "error": "unknown_decision", "decision": d}
        elif d not in assessment.get("available_decisions", []):
            return {"ok": False, "error": "decision_not_available", "decision": d, "assessment": assessment}

    from hg_runtime.bounded_soak.stop_panic_runtime import write_stop_receipt
    from hg_runtime.social_capability.review_queue import pause_live_publish

    if d == ActiveRunDecision.PAUSE_PUBLISH.value:
        result = pause_live_publish(run_dir, reason="active_run_decision")
        return {"ok": True, "decision": d, "result": result}
    if d == ActiveRunDecision.STOP_RUN.value:
        stop_file = ws / ".hg-local" / "soak" / "STOP"
        stop_file.parent.mkdir(parents=True, exist_ok=True)
        stop_file.write_text("operator stop\n", encoding="utf-8")
        receipt = write_stop_receipt(ws, run_dir=run_dir, operator_ref=operator_ref)
        return {"ok": True, "decision": d, "receipt_ref": receipt}
    if d == ActiveRunDecision.READ_DRAFT_ONLY.value:
        control = _read_json(run_dir / "run_control.json") or {}
        control["allow_live_social_publish"] = False
        control["read_draft_only"] = True
        control["updated_at"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "run_control.json").write_text(json.dumps(control, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "decision": d}
    if d == ActiveRunDecision.CONTINUE_APPROVED_ONLY_WITH_OBSERVER.value:
        ok, age = _observer_fresh(run_dir)
        if not ok:
            return {"ok": False, "error": "observer_not_fresh", "age": age}
        control = _read_json(run_dir / "run_control.json") or {}
        control["approved_only_mode"] = True
        control["updated_at"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "run_control.json").write_text(json.dumps(control, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "decision": d}
    return {"ok": False, "error": "not_implemented", "decision": d}


def can_publish_on_active_run(*, workspace: Path | None = None) -> tuple[bool, str]:
    assessment = assess_active_run(workspace=workspace)
    if assessment["verdict"] == "RED_ACTIVE_RUN_PUBLISH_ENABLED_WITHOUT_OBSERVER":
        return False, assessment["verdict"]
    if assessment.get("panic_active") or assessment.get("stop_active"):
        return False, "stop_or_panic_active"
    return True, assessment.get("verdict", "ok")


__all__ = [
    "ActiveRunDecision",
    "active_soak_run_dir",
    "apply_active_run_decision",
    "assess_active_run",
    "can_publish_on_active_run",
    "event_timestamp",
    "observer_event_lines",
    "soak_event_lines",
]
