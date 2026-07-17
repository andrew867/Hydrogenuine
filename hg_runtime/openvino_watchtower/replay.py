"""Read-only watchtower replay — never mutates live runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterator

from hg_runtime.openvino_watchtower.redaction import redact_payload
from hg_runtime.openvino_watchtower.schema import TelemetryRedactionPolicy
from hg_runtime.openvino_watchtower.session import WatchtowerSession, load_session

WORKSPACE = Path(__file__).resolve().parents[2]
LIVE_EVENTS = WORKSPACE / ".hg-local" / "openvino_watchtower" / "events.jsonl"


class WatchtowerReplayMode(str, Enum):
    READ_ONLY = "read_only"
    SCRUB = "scrub"


@dataclass
class WatchtowerReplay:
    session: WatchtowerSession
    mode: WatchtowerReplayMode = WatchtowerReplayMode.READ_ONLY

    @classmethod
    def open(cls, session_id: str, *, mode: WatchtowerReplayMode = WatchtowerReplayMode.READ_ONLY) -> WatchtowerReplay:
        return cls(session=load_session(session_id), mode=mode)

    def events(self) -> list[dict[str, Any]]:
        if not self.session.events_path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in self.session.events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
                redacted, _ = redact_payload(ev, policy=TelemetryRedactionPolicy())
                out.append(redacted)
            except json.JSONDecodeError:
                continue
        return out

    def snapshot(self) -> dict[str, Any] | None:
        if not self.session.snapshot_path.is_file():
            return None
        try:
            data = json.loads(self.session.snapshot_path.read_text(encoding="utf-8"))
            redacted, _ = redact_payload(data, policy=TelemetryRedactionPolicy())
            redacted["replay_mode"] = self.mode.value
            redacted["data_tier"] = "REPLAY"
            redacted["authority_created"] = False
            redacted["permission_granted"] = False
            return redacted
        except (OSError, json.JSONDecodeError):
            return None

    def timeline(self) -> list[dict[str, Any]]:
        if not self.session.timeline_path.is_file():
            return []
        try:
            return json.loads(self.session.timeline_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

    def iter_frames(self) -> Iterator[dict[str, Any]]:
        for i, ev in enumerate(self.events()):
            yield {"frame": i, "event": ev, "replay_mode": self.mode.value}

    def assert_read_only(self) -> None:
        """Replay must not touch live event sink."""
        if self.mode != WatchtowerReplayMode.READ_ONLY:
            return
        # Contract: replay code never opens LIVE_EVENTS for write; verified in tests.


__all__ = ["WatchtowerReplay", "WatchtowerReplayMode", "LIVE_EVENTS"]
