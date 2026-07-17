"""Extended dry autonomy run state persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyState, now_iso
from hg_runtime.extended_dry_autonomy.storage import run_dir, write_json


@dataclass
class ExtendedRunStore:
    run_id: str
    base: Path | None = None

    @property
    def root(self) -> Path:
        return run_dir(self.run_id, base=self.base)

    def write_config(self, payload: dict[str, Any]) -> Path:
        return write_json(self.root / "config.json", payload)

    def write_run(self, payload: dict[str, Any]) -> Path:
        return write_json(self.root / "run.json", payload)

    def read_run(self) -> dict[str, Any] | None:
        path = self.root / "run.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def append_iteration(self, payload: dict[str, Any]) -> None:
        with (self.root / "iterations.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")

    def append_heartbeat(self, payload: dict[str, Any]) -> None:
        with (self.root / "heartbeats.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")

    def write_state_snapshot(
        self,
        *,
        status: ExtendedDryAutonomyState,
        iteration_count: int,
        last_turn_ref: str | None,
        verdict: str | None = None,
        paused: bool = False,
    ) -> Path:
        return write_json(
            self.root / "state.json",
            {
                "run_id": self.run_id,
                "status": status.value,
                "iteration_count": iteration_count,
                "last_turn_ref": last_turn_ref,
                "verdict": verdict,
                "paused": paused,
                "updated_at": now_iso(),
            },
        )


__all__ = ["ExtendedRunStore"]
