"""Watchtower event emission and JSONL sink."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Callable

from hg_runtime.openvino_watchtower.redaction import redact_payload
from hg_runtime.openvino_watchtower.schema import (
    EventType,
    InferenceEvent,
    TelemetryRedactionPolicy,
)

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_EVENT_PATH = WORKSPACE / ".hg-local" / "openvino_watchtower" / "events.jsonl"

_lock = threading.Lock()
_listeners: list[Callable[[dict[str, Any]], None]] = []
_policy = TelemetryRedactionPolicy()
_event_path: Path = DEFAULT_EVENT_PATH


def configure_events(*, path: Path | None = None, policy: TelemetryRedactionPolicy | None = None) -> None:
    global _event_path, _policy
    if path is not None:
        _event_path = path
    if policy is not None:
        _policy = policy


def add_listener(fn: Callable[[dict[str, Any]], None]) -> None:
    _listeners.append(fn)


def remove_listener(fn: Callable[[dict[str, Any]], None]) -> None:
    if fn in _listeners:
        _listeners.remove(fn)


def emit_event(
    event_type: EventType,
    *,
    span_id: str | None = None,
    request_id: str | None = None,
    organ_id: str | None = None,
    model_id: str | None = None,
    device: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = InferenceEvent(
        event_type=event_type,
        span_id=span_id,
        request_id=request_id,
        organ_id=organ_id,
        model_id=model_id,
        device=device,
        payload=payload or {},
    )
    raw = event.to_dict()
    redacted, applied = redact_payload(raw, policy=_policy)
    if applied:
        redacted.setdefault("payload", {})["redaction_applied"] = applied
    _append_jsonl(redacted)
    for listener in list(_listeners):
        try:
            listener(redacted)
        except Exception:
            pass
    return redacted


def _append_jsonl(record: dict[str, Any]) -> None:
    with _lock:
        _event_path.parent.mkdir(parents=True, exist_ok=True)
        with _event_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")


def read_recent_events(limit: int = 200, *, path: Path | None = None) -> list[dict[str, Any]]:
    p = path or _event_path
    if not p.is_file():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def watchtower_enabled() -> bool:
    return os.environ.get("HG_OPENVINO_WATCHTOWER_ENABLED", "").lower() in {"1", "true", "yes"}


def watchtower_strict() -> bool:
    return os.environ.get("HG_OPENVINO_WATCHTOWER_STRICT", "").lower() in {"1", "true", "yes"}


def default_port() -> int:
    try:
        return int(os.environ.get("HG_OPENVINO_WATCHTOWER_PORT", "8791"))
    except ValueError:
        return 8791


__all__ = [
    "DEFAULT_EVENT_PATH",
    "add_listener",
    "configure_events",
    "default_port",
    "emit_event",
    "read_recent_events",
    "remove_listener",
    "watchtower_enabled",
    "watchtower_strict",
]
