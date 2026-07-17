"""check_steering(run_id, run_dir): apply pending steering (cancel/pause/inject). Phase 8."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .store import default_steering_store

# Module-level default store; set by operator_console or tests.
_default_store = None


def set_default_store(store) -> None:
    global _default_store
    _default_store = store


def get_default_store():
    return _default_store


def get_pending(run_id: str, store=None) -> List[Dict[str, Any]]:
    """Return unconsumed steering events for run_id. Uses default store if store is None."""
    s = store or _default_store
    if s is None:
        try:
            s = default_steering_store()
        except Exception:
            return []
    return s.get_pending(run_id)


def check_steering(
    run_id: str,
    run_dir: Optional[Path] = None,
    store=None,
    pause_poll_interval: float = 1.0,
    pause_max_wait: Optional[float] = None,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Process pending steering events for run_id.
    Returns (action, inject_payload) where action is "continue" | "cancel" | "inject".
    - cancel: caller should exit loop (we write cancel file here so is_cancel_requested sees it).
    - pause: we block until a "resume" event or timeout, then return ("continue", None).
    - inject: return ("inject", payload) for caller to merge into context.
    """
    events = get_pending(run_id, store)
    if not events:
        return "continue", None

    s = store or _default_store
    if s is None:
        try:
            s = default_steering_store()
        except Exception:
            return "continue", None
    for evt in events:
        kind = (evt.get("kind") or "").strip().lower()
        payload = evt.get("payload") or {}
        steering_id = evt.get("steering_id")

        if kind == "cancel":
            if s and steering_id:
                s.mark_consumed(steering_id)
            if run_dir:
                try:
                    from hg_core.task_graph.cancel import write_cancel_request
                    write_cancel_request(Path(run_dir), run_id, reason=payload.get("reason", ""), source="steering")
                except Exception:
                    pass
            return "cancel", None

        if kind == "pause":
            if s and steering_id:
                s.mark_consumed(steering_id)
            waited = 0.0
            while True:
                time.sleep(pause_poll_interval)
                waited += pause_poll_interval
                if pause_max_wait is not None and waited >= pause_max_wait:
                    break
                remaining = get_pending(run_id, store)
                if any((e.get("kind") or "").strip().lower() == "resume" for e in remaining):
                    for e in remaining:
                        if (e.get("kind") or "").strip().lower() == "resume" and s and e.get("steering_id"):
                            s.mark_consumed(e["steering_id"])
                    break
            return "continue", None

        if kind == "inject":
            if s and steering_id:
                s.mark_consumed(steering_id)
            return "inject", payload

    return "continue", None
