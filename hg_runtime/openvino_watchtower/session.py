"""Watchtower session recorder — append-only telemetry sessions."""

from __future__ import annotations

import json
import shutil
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from hg_runtime.openvino_watchtower.events import add_listener, remove_listener
from hg_runtime.openvino_watchtower.redaction import redact_payload
from hg_runtime.openvino_watchtower.schema import TelemetryRedactionPolicy

WORKSPACE = Path(__file__).resolve().parents[2]
SESSIONS_ROOT = WORKSPACE / ".hg-local" / "openvino_watchtower" / "sessions"

_lock = threading.Lock()
_active_session_id: str | None = None
_session_listener_registered = False


def _on_live_event(event: dict[str, Any]) -> None:
    sid = active_session_id()
    if not sid:
        return
    try:
        load_session(sid).append_event(event)
    except FileNotFoundError:
        pass


def _register_session_listener() -> None:
    global _session_listener_registered
    if not _session_listener_registered:
        add_listener(_on_live_event)
        _session_listener_registered = True


def _unregister_session_listener() -> None:
    global _session_listener_registered
    if _session_listener_registered:
        remove_listener(_on_live_event)
        _session_listener_registered = False


@dataclass
class WatchtowerSessionManifest:
    session_id: str
    started_at: str
    stopped_at: str | None = None
    event_count: int = 0
    replay_mode: str = "read_only"
    authority_created: bool = False
    permission_granted: bool = False
    advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WatchtowerSession:
    session_id: str
    root: Path
    manifest: WatchtowerSessionManifest
    events_path: Path
    snapshot_path: Path
    timeline_path: Path
    manifest_path: Path

    @classmethod
    def open(cls, session_id: str | None = None, *, root: Path | None = None) -> WatchtowerSession:
        sid = session_id or f"sess-{uuid4().hex[:12]}"
        base = (root or SESSIONS_ROOT) / sid
        base.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        manifest = WatchtowerSessionManifest(session_id=sid, started_at=now)
        session = cls(
            session_id=sid,
            root=base,
            manifest=manifest,
            events_path=base / "events.jsonl",
            snapshot_path=base / "snapshot.json",
            timeline_path=base / "timeline.json",
            manifest_path=base / "manifest.json",
        )
        session._write_manifest()
        return session

    def _write_manifest(self) -> None:
        self.manifest_path.write_text(json.dumps(self.manifest.to_dict(), indent=2), encoding="utf-8")

    def append_event(self, event: dict[str, Any]) -> None:
        redacted, _ = redact_payload(event, policy=TelemetryRedactionPolicy())
        with _lock:
            with self.events_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(redacted, sort_keys=True) + "\n")
            self.manifest.event_count += 1
            self._write_manifest()

    def copy_live_events(self) -> int:
        count = 0
        for ev in read_recent_events(limit=10_000, path=DEFAULT_EVENT_PATH):
            self.append_event(ev)
            count += 1
        return count

    def write_snapshot(self, snapshot: dict[str, Any]) -> None:
        redacted, _ = redact_payload(snapshot, policy=TelemetryRedactionPolicy())
        self.snapshot_path.write_text(json.dumps(redacted, indent=2, sort_keys=True), encoding="utf-8")

    def write_timeline(self, timeline: list[dict[str, Any]]) -> None:
        self.timeline_path.write_text(json.dumps(timeline, indent=2), encoding="utf-8")

    def stop(self) -> WatchtowerSessionManifest:
        self.manifest.stopped_at = datetime.now(timezone.utc).isoformat()
        self._write_manifest()
        return self.manifest


def start_session(session_id: str | None = None) -> WatchtowerSession:
    global _active_session_id
    with _lock:
        if _active_session_id:
            raise RuntimeError(f"session already active: {_active_session_id}")
        session = WatchtowerSession.open(session_id)
        _active_session_id = session.session_id
    _register_session_listener()
    return session


def stop_session(*, snapshot: dict[str, Any] | None = None, timeline: list[dict[str, Any]] | None = None) -> WatchtowerSessionManifest | None:
    global _active_session_id
    with _lock:
        sid = _active_session_id
        _active_session_id = None
    if not sid:
        return None
    session = load_session(sid)
    if snapshot:
        session.write_snapshot(snapshot)
    if timeline:
        session.write_timeline(timeline)
    manifest = session.stop()
    _unregister_session_listener()
    return manifest


def active_session_id() -> str | None:
    return _active_session_id


def list_sessions(*, root: Path | None = None) -> list[dict[str, Any]]:
    base = root or SESSIONS_ROOT
    if not base.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for d in sorted(base.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        manifest = d / "manifest.json"
        if manifest.is_file():
            try:
                out.append(json.loads(manifest.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                out.append({"session_id": d.name, "corrupt": True})
    return out


def load_session(session_id: str, *, root: Path | None = None) -> WatchtowerSession:
    base = (root or SESSIONS_ROOT) / session_id
    if not base.is_dir():
        raise FileNotFoundError(session_id)
    manifest_data = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    manifest = WatchtowerSessionManifest(**{k: manifest_data[k] for k in WatchtowerSessionManifest.__dataclass_fields__ if k in manifest_data})
    return WatchtowerSession(
        session_id=session_id,
        root=base,
        manifest=manifest,
        events_path=base / "events.jsonl",
        snapshot_path=base / "snapshot.json",
        timeline_path=base / "timeline.json",
        manifest_path=base / "manifest.json",
    )


__all__ = [
    "SESSIONS_ROOT",
    "WatchtowerSession",
    "WatchtowerSessionManifest",
    "active_session_id",
    "list_sessions",
    "load_session",
    "start_session",
    "stop_session",
]
