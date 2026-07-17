"""Session heartbeat."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.hands_off_session.schema import new_id, now_iso, session_dir


@dataclass
class SessionHeartbeat:
    heartbeat_id: str
    session_id: str
    pid: int
    turn_count: int
    status: str
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "heartbeat_id": self.heartbeat_id,
            "session_id": self.session_id,
            "pid": self.pid,
            "turn_count": self.turn_count,
            "status": self.status,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> SessionHeartbeat:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return SessionHeartbeat(**{**self.__dict__, "hash": compute_record_hash(body)})


def heartbeat_dir(session_id: str, *, base: Path | None = None) -> Path:
    return session_dir(session_id, base=base) / "heartbeats"


def write_heartbeat(
    *,
    session_id: str,
    pid: int,
    turn_count: int,
    status: str,
    base: Path | None = None,
) -> SessionHeartbeat:
    hb = SessionHeartbeat(
        heartbeat_id=new_id("sess-hb"),
        session_id=session_id,
        pid=pid,
        turn_count=turn_count,
        status=status,
        created_at=now_iso(),
    ).with_hash()
    d = heartbeat_dir(session_id, base=base)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{hb.heartbeat_id}.json").write_text(json.dumps(hb.to_payload(), indent=2) + "\n", encoding="utf-8")
    latest = session_dir(session_id, base=base) / "latest_heartbeat.json"
    latest.write_text(json.dumps(hb.to_payload(), indent=2) + "\n", encoding="utf-8")
    return hb


def load_latest_heartbeat(session_id: str, *, base: Path | None = None) -> SessionHeartbeat | None:
    path = session_dir(session_id, base=base) / "latest_heartbeat.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionHeartbeat(
        heartbeat_id=data["heartbeat_id"],
        session_id=data["session_id"],
        pid=int(data["pid"]),
        turn_count=int(data["turn_count"]),
        status=data["status"],
        created_at=data["created_at"],
        hash=data.get("hash"),
    )
