"""Current-run pointer reconciliation.

A finalized soak run is *done*: its historical ``allow_live_social_publish`` flag is a record of
what the run was permitted to do, not a live risk. A ``current_run.txt`` pointer that still points at
a finalized run is **stale** and must not be read as "a publish-enabled run is live right now".

This module classifies the pointer and (optionally) clears a stale one. It changes no soak state and
never enables or pauses publish — it only makes the pointer honest. The live-risk decision still
belongs to ``assess_active_run`` (an *active* publish-enabled run with no fresh observer is still RED).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]


def _pointer_path(ws: Path) -> Path:
    return ws / ".hg-local" / "soak" / "current_run.txt"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def run_is_finalized(run_dir: Path) -> bool:
    summary = _read_json(run_dir / "final_summary.json")
    return bool(summary and summary.get("finalized_at"))


def run_is_active(run_dir: Path) -> bool:
    from hg_runtime.bounded_soak.active_run import _run_is_active

    return _run_is_active(run_dir)


def read_pointer(workspace: Path | None = None) -> str | None:
    ws = workspace or WORKSPACE
    p = _pointer_path(ws)
    if not p.is_file():
        return None
    raw = p.read_text(encoding="utf-8").strip()
    return raw or None


def _resolve(ws: Path, raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = ws / p
    return p


def current_run_state(workspace: Path | None = None) -> dict[str, Any]:
    """Classify the current-run pointer without changing anything."""
    ws = workspace or WORKSPACE
    raw = read_pointer(ws)
    if not raw:
        return {
            "pointer": None,
            "target_run_dir": None,
            "target_exists": False,
            "finalized": False,
            "active": False,
            "publish_enabled": False,
            "classification": "NO_POINTER",
            "is_stale": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
    target = _resolve(ws, raw)
    exists = target.is_dir()
    finalized = exists and run_is_finalized(target)
    active = exists and run_is_active(target)
    control = _read_json(target / "run_control.json") or {}
    publish_enabled = bool(control.get("allow_live_social_publish", False))

    if not exists:
        classification = "MISSING_TARGET"
        is_stale = True
    elif active and not finalized:
        classification = "ACTIVE"
        is_stale = False
    elif finalized:
        classification = "STALE_FINALIZED_POINTER"
        is_stale = True
    else:
        classification = "ENDED_NOT_FINALIZED"
        is_stale = False

    return {
        "pointer": raw,
        "target_run_dir": str(target),
        "target_exists": exists,
        "finalized": finalized,
        "active": active,
        "publish_enabled": publish_enabled,
        "classification": classification,
        "is_stale": is_stale,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def reconcile_current_run(workspace: Path | None = None, *, apply: bool = False) -> dict[str, Any]:
    """Classify the pointer; if ``apply`` and the pointer is stale, clear it (no-active-run marker).

    Clearing writes an empty pointer file — the honest "no active run" state. A finalized run's
    publish flag is never treated as live. This does not stop/start a soak or change publish state.
    """
    ws = workspace or WORKSPACE
    state = current_run_state(ws)
    pointer_before = state["pointer"]
    applied = False
    pointer_after = pointer_before

    if apply and state["is_stale"]:
        p = _pointer_path(ws)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")
        applied = True
        pointer_after = None

    return {
        "pointer_before": pointer_before,
        "pointer_after": pointer_after,
        "classification": state["classification"],
        "is_stale": state["is_stale"],
        "finalized": state["finalized"],
        "active": state["active"],
        "publish_enabled": state["publish_enabled"],
        "applied": applied,
        "human_message": _message(state, applied),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def _message(state: dict[str, Any], applied: bool) -> str:
    c = state["classification"]
    if c == "NO_POINTER":
        return "No current-run pointer — no active soak run."
    if c == "ACTIVE":
        return "Current run is active."
    if c == "STALE_FINALIZED_POINTER":
        return "Pointer targets a finalized run — stale, cleared." if applied else (
            "Pointer targets a finalized run — stale (run-only classification, not cleared)."
        )
    if c == "ENDED_NOT_FINALIZED":
        return "Run ended but not finalized — operator should finalize."
    if c == "MISSING_TARGET":
        return "Pointer targets a missing run dir — stale, cleared." if applied else "Pointer targets a missing run dir — stale."
    return c


__all__ = [
    "current_run_state",
    "reconcile_current_run",
    "read_pointer",
    "run_is_active",
    "run_is_finalized",
]
