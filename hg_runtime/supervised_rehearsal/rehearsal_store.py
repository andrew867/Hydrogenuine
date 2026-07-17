"""Local supervised rehearsal store."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.supervised_rehearsal.errors import RehearsalError
from hg_runtime.supervised_rehearsal.schema import (
    PostflightSummary,
    SupervisedRehearsalConfig,
    SupervisedRehearsalResult,
    SupervisedRehearsalRun,
)


def rehearsal_root(*, base: Path | None = None) -> Path:
    env_root = os.environ.get("HG_REHEARSAL_ROOT")
    if env_root:
        return Path(env_root)
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "rehearsals"
    return root


def current_lock_path(*, base: Path | None = None) -> Path:
    return rehearsal_root(base=base) / "current_run.lock"


def run_rehearsal_dir(run_id: str, *, base: Path | None = None) -> Path:
    return rehearsal_root(base=base) / run_id


def _write_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RehearsalError(f"record already exists: {path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _write_overwrite(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


@dataclass
class RehearsalStore:
    run_id: str
    base: Path | None = None

    @property
    def root(self) -> Path:
        return run_rehearsal_dir(self.run_id, base=self.base)

    @property
    def config_path(self) -> Path:
        return self.root / "config.json"

    @property
    def run_path(self) -> Path:
        return self.root / "run.json"

    @property
    def result_path(self) -> Path:
        return self.root / "result.json"

    @property
    def postflight_path(self) -> Path:
        return self.root / "postflight.json"

    @property
    def observer_dir(self) -> Path:
        return self.root / "observer"

    @property
    def turn_summaries_path(self) -> Path:
        return self.root / "turn_summaries.jsonl"

    def store_config(self, config: SupervisedRehearsalConfig) -> Path:
        return _write_atomic(self.config_path, config.to_payload())

    def read_config(self) -> dict[str, Any]:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def store_run(self, run: SupervisedRehearsalRun) -> Path:
        return _write_overwrite(self.run_path, run.to_payload())

    def read_run(self) -> dict[str, Any] | None:
        if not self.run_path.is_file():
            return None
        return json.loads(self.run_path.read_text(encoding="utf-8"))

    def append_turn_summary(self, summary: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.turn_summaries_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(summary, sort_keys=True) + "\n")

    def read_turn_summaries(self) -> list[dict[str, Any]]:
        if not self.turn_summaries_path.is_file():
            return []
        return [json.loads(line) for line in self.turn_summaries_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def store_result(self, result: SupervisedRehearsalResult) -> Path:
        return _write_overwrite(self.result_path, result.to_payload())

    def read_result(self) -> dict[str, Any] | None:
        if not self.result_path.is_file():
            return None
        return json.loads(self.result_path.read_text(encoding="utf-8"))

    def store_postflight(self, summary: PostflightSummary) -> Path:
        return _write_overwrite(self.postflight_path, summary.to_payload())

    def read_postflight(self) -> dict[str, Any] | None:
        if not self.postflight_path.is_file():
            return None
        return json.loads(self.postflight_path.read_text(encoding="utf-8"))

    def store_observer_heartbeat(self, heartbeat: dict[str, Any]) -> Path:
        idx = heartbeat.get("heartbeat_index", 0)
        path = self.observer_dir / f"heartbeat-{idx:04d}.json"
        return _write_atomic(path, heartbeat)

    def latest_observer_heartbeat(self) -> dict[str, Any] | None:
        if not self.observer_dir.is_dir():
            return None
        files = sorted(self.observer_dir.glob("heartbeat-*.json"))
        if not files:
            return None
        return json.loads(files[-1].read_text(encoding="utf-8"))


__all__ = ["RehearsalStore", "current_lock_path", "rehearsal_root", "run_rehearsal_dir"]
