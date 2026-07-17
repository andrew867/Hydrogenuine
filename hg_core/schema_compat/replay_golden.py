"""Golden replay fixture compatibility (CT-09 SCH)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.replay import replay

from hg_core.schema_compat.registry import GoldenFixture, SchemaRegistry, load_registry
from hg_core.schema_compat.validator import REASON_VERSION_UNSUPPORTED, migration_error


@dataclass(frozen=True)
class GoldenReplayResult:
    fixture_id: str
    ok: bool
    expected_state_hash: str
    actual_state_hash: str
    detail: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "ok": self.ok,
            "expected_state_hash": self.expected_state_hash,
            "actual_state_hash": self.actual_state_hash,
            "detail": self.detail,
        }


def run_golden_fixture(
    fixture: GoldenFixture,
    *,
    workspace: Path,
    registry: SchemaRegistry | None = None,
) -> GoldenReplayResult:
    loaded = registry or load_registry(workspace=workspace)
    fixture_path = Path(fixture.path)
    fixture_dir = fixture_path if fixture_path.is_absolute() else workspace / fixture.path
    meta_path = fixture_dir / "fixture_meta.json"
    if not meta_path.exists():
        return GoldenReplayResult(
            fixture.fixture_id,
            False,
            fixture.expected_state_hash,
            "",
            "missing fixture_meta.json",
        )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta_version = int(meta.get("schema_version", 1))
    entry = loaded.entry(fixture.schema_id, meta_version)
    if entry is None:
        err = migration_error(
            fixture.schema_id,
            meta_version,
            meta_version,
            REASON_VERSION_UNSUPPORTED,
        )
        return GoldenReplayResult(
            fixture.fixture_id,
            False,
            fixture.expected_state_hash,
            "",
            json.dumps(err),
        )
    runtime_dir = fixture_dir / "runtime"
    if not runtime_dir.exists():
        return GoldenReplayResult(
            fixture.fixture_id,
            False,
            fixture.expected_state_hash,
            "",
            "missing runtime log directory",
        )
    result = replay(runtime_dir)
    if result.chain_error:
        return GoldenReplayResult(
            fixture.fixture_id,
            False,
            fixture.expected_state_hash,
            result.state_hash,
            result.chain_error,
        )
    ok = result.state_hash == fixture.expected_state_hash and result.ok
    return GoldenReplayResult(
        fixture.fixture_id,
        ok,
        fixture.expected_state_hash,
        result.state_hash,
        "replay ok" if ok else "state hash mismatch",
    )


def run_golden_replay_matrix(
    registry: SchemaRegistry | None = None,
    *,
    workspace: Path | None = None,
) -> list[GoldenReplayResult]:
    root = workspace or Path(__file__).resolve().parents[2]
    loaded = registry or load_registry(workspace=root)
    return [run_golden_fixture(fixture, workspace=root, registry=loaded) for fixture in loaded.golden_fixtures]


__all__ = ["GoldenReplayResult", "run_golden_fixture", "run_golden_replay_matrix"]
