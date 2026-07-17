from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from hg_crr.checkpoint_manager import CheckpointManager
from hg_runtime.bus import EventBus
from hg_runtime import world_state as ws


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T01:00:{counter['value']:02d}.000000Z"

    return tick


def _runtime(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    bus.emit("TIMER_EVENT", {"timer_id": "ckpt"}, source="timer")
    events = list(bus.read_all())
    state = ws.apply_many(ws.initial_state(), events)
    return bus, state


def test_checkpoint_manifest_creation_and_schema(tmp_path: Path):
    bus, state = _runtime(tmp_path)
    manager = CheckpointManager(tmp_path / "checkpoints")
    record = manager.create_from_runtime(
        bus=bus,
        world_state=state,
        checkpoint_id="ckpt_test",
        cycle_ref="crr_test",
        created_at="2026-06-11T01:00:00.000000Z",
    )

    validate(
        instance=dict(record.manifest),
        schema=json.loads(
            Path("docs/schemas/crr_checkpoint_manifest_v1.json").read_text(encoding="utf-8")
        ),
    )
    heads = record.manifest["evidence_chain_heads"]
    assert heads["rtc_event_log"].startswith("sha256:")
    assert heads["rtc_event_seq"] == 0
    assert heads["rtc_world_state_hash"].startswith("sha256:")
    assert (record.directory / "manifest.json").exists()
    assert (record.directory / "arousal.json").exists()


def test_checkpoint_manifest_is_immutable_after_creation(tmp_path: Path):
    bus, state = _runtime(tmp_path)
    manager = CheckpointManager(tmp_path / "checkpoints")
    record = manager.create_from_runtime(
        bus=bus,
        world_state=state,
        checkpoint_id="ckpt_immutable",
        cycle_ref="crr_immutable",
        created_at="2026-06-11T01:00:00.000000Z",
    )
    on_disk_before = (record.directory / "manifest.json").read_text(encoding="utf-8")
    mutable = dict(record.manifest)
    mutable["kind"] = "full"
    mutable["evidence_chain_heads"] = {"rtc_event_log": "sha256:tampered", "rtc_event_seq": 99}
    on_disk_after = (record.directory / "manifest.json").read_text(encoding="utf-8")
    assert on_disk_before == on_disk_after
    loaded = manager.load("ckpt_immutable")
    assert loaded.manifest["kind"] == "incremental"


def test_checkpoint_creation_does_not_mutate_protected_artifacts(tmp_path: Path):
    bus, state = _runtime(tmp_path)
    event_log_bytes = b"".join(
        path.read_bytes() for path in sorted((tmp_path / "runtime").glob("events-*.jsonl"))
    )
    manager = CheckpointManager(tmp_path / "checkpoints")
    manager.create_from_runtime(
        bus=bus,
        world_state=state,
        checkpoint_id="ckpt_safe",
        cycle_ref="crr_safe",
        created_at="2026-06-11T01:00:00.000000Z",
    )
    event_log_bytes_after = b"".join(
        path.read_bytes() for path in sorted((tmp_path / "runtime").glob("events-*.jsonl"))
    )
    assert event_log_bytes == event_log_bytes_after
    assert bus.verify_chain()["ok"] is True


def test_loaded_checkpoint_matches_event_log_and_world_state_continuity(tmp_path: Path):
    bus, state = _runtime(tmp_path)
    manager = CheckpointManager(tmp_path / "checkpoints")
    record = manager.create_from_runtime(
        bus=bus,
        world_state=state,
        checkpoint_id="ckpt_continuity",
        cycle_ref="crr_continuity",
        created_at="2026-06-11T01:00:00.000000Z",
    )
    loaded = manager.load("ckpt_continuity")
    assert manager.validate_continuity(loaded, bus=bus, world_state=state) is True
    assert loaded.manifest["evidence_chain_heads"] == record.manifest["evidence_chain_heads"]

    bus.emit("TIMER_EVENT", {"timer_id": "after"}, source="timer")
    events = list(bus.read_all())
    grown_state = ws.apply_many(state, events[1:])
    assert manager.validate_continuity(loaded, bus=bus, world_state=grown_state) is True


def test_checkpoint_rejects_rewound_event_log(tmp_path: Path):
    bus, state = _runtime(tmp_path)
    manager = CheckpointManager(tmp_path / "checkpoints")
    record = manager.create_from_runtime(
        bus=bus,
        world_state=state,
        checkpoint_id="ckpt_rewind",
        cycle_ref="crr_rewind",
        created_at="2026-06-11T01:00:00.000000Z",
    )
    tampered_manifest = dict(record.manifest)
    tampered_heads = dict(tampered_manifest["evidence_chain_heads"])
    tampered_heads["rtc_event_seq"] = 99
    tampered_manifest["evidence_chain_heads"] = tampered_heads
    from hg_crr.checkpoint_manager import CheckpointRecord

    bad_record = CheckpointRecord(manifest=tampered_manifest, directory=record.directory)
    assert manager.validate_continuity(bad_record, bus=bus, world_state=state) is False
