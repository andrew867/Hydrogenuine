"""Session postflight."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.hands_off_session.schema import HandsOffSessionVerdict, new_id, now_iso, session_dir


@dataclass
class SessionPostflight:
    postflight_id: str
    session_id: str
    verdict: str
    turn_count: int
    selected_task_count: int
    idle_count: int
    stop_requested: bool
    panic_requested: bool
    external_side_effect_count: int
    background_process_survives: bool
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "postflight_id": self.postflight_id,
            "session_id": self.session_id,
            "verdict": self.verdict,
            "turn_count": self.turn_count,
            "selected_task_count": self.selected_task_count,
            "idle_count": self.idle_count,
            "stop_requested": self.stop_requested,
            "panic_requested": self.panic_requested,
            "external_side_effect_count": self.external_side_effect_count,
            "background_process_survives": self.background_process_survives,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> SessionPostflight:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return SessionPostflight(**{**self.__dict__, "hash": compute_record_hash(body)})


def postflight_path(session_id: str, *, base: Path | None = None) -> Path:
    return session_dir(session_id, base=base) / "postflight.json"


def write_postflight(postflight: SessionPostflight, *, base: Path | None = None) -> Path:
    path = postflight_path(postflight.session_id, base=base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(postflight.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_postflight(session_id: str, *, base: Path | None = None) -> SessionPostflight | None:
    path = postflight_path(session_id, base=base)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionPostflight(
        postflight_id=data["postflight_id"],
        session_id=data["session_id"],
        verdict=data["verdict"],
        turn_count=int(data.get("turn_count", 0)),
        selected_task_count=int(data.get("selected_task_count", 0)),
        idle_count=int(data.get("idle_count", 0)),
        stop_requested=bool(data.get("stop_requested")),
        panic_requested=bool(data.get("panic_requested")),
        external_side_effect_count=int(data.get("external_side_effect_count", 0)),
        background_process_survives=bool(data.get("background_process_survives", False)),
        created_at=data["created_at"],
        hash=data.get("hash"),
    )
