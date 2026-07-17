"""Dry soak local store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.dry_soak.storage import run_dry_soak_dir


@dataclass
class DrySoakStore:
    run_id: str
    base: Path | None = None

    @property
    def root(self) -> Path:
        return run_dry_soak_dir(self.run_id, base=self.base)

    def read_json(self, name: str) -> dict[str, Any] | None:
        path = self.root / name
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read_run(self) -> dict[str, Any] | None:
        return self.read_json("run.json")

    def read_config(self) -> dict[str, Any] | None:
        return self.read_json("config.json")

    def read_readiness(self) -> dict[str, Any] | None:
        return self.read_json("readiness_report.json")

    def read_exciton_snapshot(self) -> dict[str, Any] | None:
        return self.read_json("exciton_snapshot.json")

    def read_turn_summaries(self) -> list[dict[str, Any]]:
        path = self.root / "turn_summaries.jsonl"
        if not path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows


__all__ = ["DrySoakStore"]
