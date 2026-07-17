from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from hg_crr.checkpoint import manifest_hash
from hg_crr.checkpoint_manager import CheckpointManager, CheckpointRecord
from hg_crr.hygiene import delegate_l1_hygiene_cycle
from hg_crr.rehydrate import RehydrationVerifier, load_and_verify, observed_chain_heads
from hg_crr.trusted_snapshot import append_trusted_snapshot, build_trusted_snapshot, load_trusted_snapshots
from hg_runtime.bus import EventBus
from hg_runtime import world_state as ws
from hg_runtime.handlers import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_crr.rtc_adapter import Phase0RecoveryHandler
from hg_runtime.replay import replay


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T02:00:{counter['value']:02d}.000000Z"

    return tick


def _runtime_with_checkpoint(tmp_path: Path):
    recovery = Phase0RecoveryHandler(tmp_path / "checkpoints", requested=True)
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    loop = RuntimeLoop(
        bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=recovery,
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )
    loop.bus.submit("TIMER_EVENT", {"timer_id": "reh"}, source="timer")
    loop.run_once(poll_timeout=0.0)
    # Pick the checkpoint DIRECTORY, not the first entry by filesystem order: the
    # checkpoints dir also holds trusted_snapshots.jsonl (a file), which sorts first
    # on some filesystems (CI) and made CheckpointManager.load treat a file as a dir
    # (NotADirectoryError). Selecting the directory is order-independent.
    record = CheckpointManager(tmp_path / "checkpoints").load(
        next(d for d in sorted((tmp_path / "checkpoints").iterdir()) if d.is_dir()).name
    )
    return bus, loop.state, record, recovery


def test_rehydration_chain_grown_only_success(tmp_path: Path):
    bus, state, record, _ = _runtime_with_checkpoint(tmp_path)
    seq_before = int(record.manifest["evidence_chain_heads"]["rtc_event_seq"])
    bus.emit("TIMER_EVENT", {"timer_id": "grown"}, source="timer")
    new_event = list(bus.read_all())[-1]
    grown_state = ws.apply(state, new_event)
    assert new_event["seq"] > seq_before

    result = RehydrationVerifier().verify(record, bus=bus, world_state=grown_state)
    assert result.ok is True
    assert result.reason_code is None
    assert result.expected_heads is not None
    assert result.observed_heads is not None
    assert result.requires_dispatch_precheck is True


def _tampered_record(record: CheckpointRecord, **head_updates) -> CheckpointRecord:
    tampered = {key: value for key, value in record.manifest.items() if key != "manifest_hash"}
    heads = dict(tampered["evidence_chain_heads"])
    heads.update(head_updates)
    tampered["evidence_chain_heads"] = heads
    tampered["manifest_hash"] = manifest_hash(tampered)
    return CheckpointRecord(manifest=tampered, directory=record.directory)


def test_rehydration_chain_rewind_failure(tmp_path: Path):
    bus, state, record, _ = _runtime_with_checkpoint(tmp_path)
    bad = _tampered_record(record, rtc_event_seq=99)

    result = RehydrationVerifier().verify(bad, bus=bus, world_state=state)
    assert result.ok is False
    assert result.reason_code == "event_log_rewind_or_mismatch"
    assert result.expected_heads is not None
    assert result.observed_heads is not None


def test_rehydration_chain_mismatch_failure(tmp_path: Path):
    bus, state, record, _ = _runtime_with_checkpoint(tmp_path)
    bad = _tampered_record(record, rtc_event_log="sha256:" + "0" * 64)

    result = RehydrationVerifier().verify(bad, bus=bus, world_state=state)
    assert result.ok is False
    assert result.reason_code == "event_log_rewind_or_mismatch"


def test_rehydration_rejects_missing_chain_heads(tmp_path: Path):
    bus, state, record, _ = _runtime_with_checkpoint(tmp_path)
    tampered = {key: value for key, value in record.manifest.items() if key != "manifest_hash"}
    tampered["evidence_chain_heads"] = {}
    tampered["manifest_hash"] = manifest_hash(tampered)
    bad = CheckpointRecord(manifest=tampered, directory=record.directory)

    result = RehydrationVerifier().verify(bad, bus=bus, world_state=state)
    assert result.ok is False
    assert result.reason_code == "missing_chain_heads"


def test_rehydration_does_not_mutate_evidence(tmp_path: Path):
    bus, state, record, _ = _runtime_with_checkpoint(tmp_path)
    before = b"".join(
        path.read_bytes() for path in sorted((tmp_path / "runtime").glob("events-*.jsonl"))
    )
    RehydrationVerifier().verify(record, bus=bus, world_state=state)
    after = b"".join(
        path.read_bytes() for path in sorted((tmp_path / "runtime").glob("events-*.jsonl"))
    )
    assert before == after


def test_rehydration_requires_dispatch_precheck_not_authority_refresh(tmp_path: Path):
    bus, state, record, _ = _runtime_with_checkpoint(tmp_path)
    result = load_and_verify(record.directory, bus=bus, world_state=state)
    assert result.ok is True
    assert result.requires_dispatch_precheck is True
    payload = result.to_payload()
    assert "authority" not in payload
    assert "permit" not in payload
    assert payload["reason_code"] is None
    assert payload["expected_heads"]
    assert payload["observed_heads"]


def test_trusted_snapshot_verification_accepts_grown_only_chain(tmp_path: Path):
    bus, state, record, recovery = _runtime_with_checkpoint(tmp_path)
    trusted = build_trusted_snapshot(
        record,
        snapshot_id="tsnap_grown",
        runtime_config_hash="sha256:" + "a" * 64,
        promoted_at="2026-06-11T02:00:10.000000Z",
    )
    append_trusted_snapshot(recovery.trusted_registry, trusted)
    bus.emit("TIMER_EVENT", {"timer_id": "after_trusted"}, source="timer")
    grown_state = ws.apply(state, list(bus.read_all())[-1])

    result = RehydrationVerifier().verify_trusted_snapshot(trusted, bus=bus, world_state=grown_state)
    assert result.ok is True
    assert result.snapshot_id == "tsnap_grown"
    assert int(result.observed_heads["rtc_event_seq"]) > int(result.expected_heads["rtc_event_seq"])


def test_trusted_snapshot_verification_rejects_event_log_rewind(tmp_path: Path):
    bus, state, record, recovery = _runtime_with_checkpoint(tmp_path)
    trusted = build_trusted_snapshot(
        record,
        snapshot_id="tsnap_rewind",
        runtime_config_hash="sha256:" + "b" * 64,
        promoted_at="2026-06-11T02:00:10.000000Z",
    )
    append_trusted_snapshot(recovery.trusted_registry, trusted)
    tampered = dict(trusted.to_payload())
    tampered["event_log_seq"] = 99
    tampered["evidence_chain_heads"] = dict(tampered["evidence_chain_heads"])
    tampered["evidence_chain_heads"]["rtc_event_seq"] = 99

    result = RehydrationVerifier().verify_trusted_snapshot(tampered, bus=bus, world_state=state)
    assert result.ok is False
    assert result.reason_code == "trusted_event_log_rewind_or_mismatch"


def test_trusted_snapshot_registry_is_append_only(tmp_path: Path):
    bus, state, record, recovery = _runtime_with_checkpoint(tmp_path)
    snapshots_before = len(load_trusted_snapshots(recovery.trusted_registry))
    first = build_trusted_snapshot(
        record,
        snapshot_id="tsnap_a",
        runtime_config_hash="sha256:" + "c" * 64,
        promoted_at="2026-06-11T02:00:10.000000Z",
    )
    append_trusted_snapshot(recovery.trusted_registry, first)
    bytes_after_first = recovery.trusted_registry.read_bytes()
    second = build_trusted_snapshot(
        record,
        snapshot_id="tsnap_b",
        runtime_config_hash="sha256:" + "d" * 64,
        promoted_at="2026-06-11T02:00:11.000000Z",
    )
    append_trusted_snapshot(recovery.trusted_registry, second)
    bytes_after_second = recovery.trusted_registry.read_bytes()
    assert bytes_after_second.startswith(bytes_after_first)
    assert len(load_trusted_snapshots(recovery.trusted_registry)) == snapshots_before + 2


def test_checkpoint_manifest_files_are_append_only_on_disk(tmp_path: Path):
    bus, state, record, _ = _runtime_with_checkpoint(tmp_path)
    manifest_path = record.directory / "manifest.json"
    before = manifest_path.read_bytes()
    RehydrationVerifier().verify(record, bus=bus, world_state=state)
    after = manifest_path.read_bytes()
    assert before == after


def test_hygiene_cycle_delegates_without_local_transform_logic():
    import re

    results = delegate_l1_hygiene_cycle(cycle_id="crr_test")
    assert results
    assert all(result.status == "delegated_not_invoked" for result in results)
    forbidden_calls = (
        "run_gc_for_agent",
        "run_retention_job",
        "_evict_expired",
        "compact_session",
        "heavy_artifact_consolidation",
        "run_memory_maintenance",
    )
    call_pattern = re.compile(
        r"\b(" + "|".join(forbidden_calls) + r")\s*\(",
        re.IGNORECASE,
    )
    for name in ("executor_adapter.py", "hygiene.py", "l1_cycle.py", "rehydrate.py"):
        source = (Path("hg_crr") / name).read_text(encoding="utf-8")
        assert not call_pattern.search(source), f"forbidden transform call in {name}"


def test_hg_crr_modules_do_not_bypass_rtc_bus_except_adapter():
    forbidden = ("bus.emit(", "EventBus(")
    for path in Path("hg_crr").rglob("*.py"):
        if path.name.endswith("rtc_adapter.py"):
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not bypass RTC bus via {token}"


def test_recovery_verification_payload_emitted_on_rtc_bus(tmp_path: Path):
    bus, _, _, _ = _runtime_with_checkpoint(tmp_path)
    events = list(bus.read_all())
    verify_events = [event for event in events if event["type"] == "CRR_REHYDRATION_VERIFIED"]
    assert verify_events
    payload = verify_events[0]["payload"]
    assert "ok" in payload
    assert payload["ok"] is True
    assert "expected_heads" in payload
    assert "observed_heads" in payload


def test_rehydration_replay_compatibility_remains_green(tmp_path: Path):
    _runtime_with_checkpoint(tmp_path)
    result = replay(tmp_path / "runtime")
    assert result.ok is True


def test_observed_chain_heads_tracks_live_bus(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    bus.emit("TIMER_EVENT", {"timer_id": "obs"}, source="timer")
    events = list(bus.read_all())
    heads = observed_chain_heads(bus, events)
    assert heads["rtc_event_log"] == events[-1]["event_hash"]
    assert heads["rtc_event_seq"] == events[-1]["seq"]
    assert heads["governance_trace_ref"].startswith("rtc-registry:sha256:")


def test_hygiene_adapter_files_have_no_forbidden_imports():
    forbidden_prefixes = (
        "hg_core.memory_maintenance",
        "hg_core.memory_gc",
        "hg_core.heavy_artifact_consolidation",
        "hg_core.retention.worker",
        "hg_core.control_surface.cache_layer",
    )
    for name in ("executor_adapter.py", "hygiene.py"):
        tree = ast.parse((Path("hg_crr") / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                assert not module.startswith(forbidden_prefixes), f"{name} imports {module}"
