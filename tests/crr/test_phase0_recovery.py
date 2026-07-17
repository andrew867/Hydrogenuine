from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from hg_crr import Phase0RecoveryHandler, RecoveryOverlay
from hg_crr.checkpoint import build_checkpoint_manifest, verify_checkpoint_manifest
from hg_crr.executors import EXECUTOR_REGISTRY
from hg_runtime.bus import EventBus
from hg_runtime.handlers import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T01:00:{counter['value']:02d}.000000Z"

    return tick


def _loop(tmp_path: Path, recovery: Phase0RecoveryHandler) -> RuntimeLoop:
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    return RuntimeLoop(
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


def test_recovery_overlay_transitions_and_panic_preempts():
    overlay = RecoveryOverlay()

    overlay.transition("RECOVERY_PENDING")
    overlay.transition("RECOVERING")
    overlay.panic_active = True
    assert overlay.preempt("panic") == "PANIC"
    assert overlay.state == "ABORTED"
    overlay.panic_active = False
    overlay.transition("NORMAL")
    assert overlay.effective_state() == "NORMAL"

    with pytest.raises(ValueError):
        overlay.transition("RESUMING")


def test_checkpoint_manifest_records_event_log_head_not_evidence_copy():
    manifest = build_checkpoint_manifest(
        checkpoint_id="ckpt_test",
        cycle_ref="crr_test",
        created_at="2026-06-11T01:00:00.000000Z",
        kind="incremental",
        event_log_head="sha256:abc",
        event_log_seq=7,
        files={"queues.json": b"[]"},
    )

    validate(
        instance=manifest,
        schema=json.loads(
            Path("docs/schemas/crr_checkpoint_manifest_v1.json").read_text(encoding="utf-8")
        ),
    )
    assert verify_checkpoint_manifest(manifest) is True
    assert manifest["evidence_chain_heads"] == {
        "rtc_event_log": "sha256:abc",
        "rtc_event_seq": 7,
    }
    assert "ledger" not in manifest


def test_executor_registry_names_existing_primitives_without_importing_them():
    names = " ".join(ref.executor for ref in EXECUTOR_REGISTRY)
    assert "hg_core.memory_maintenance.run_memory_maintenance" in names
    assert "hg_core.retention.worker.run_retention_job" in names

    forbidden_import_prefixes = (
        "hg_core.memory_maintenance",
        "hg_core.memory_gc",
        "hg_core.heavy_artifact_consolidation",
        "hg_core.retention.worker",
        "hg_core.session_manager",
        "hg_core.control_surface.cache_layer",
    )
    crr_root = Path(__file__).parents[2] / "hg_crr"
    for path in list(crr_root.glob("*.py")) + list((crr_root / "tests").glob("*.py") if (crr_root / "tests").exists() else []):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported = [node.module or ""]
            else:
                continue
            for module in imported:
                assert not module.startswith(forbidden_import_prefixes)


def test_crr_cycle_pauses_tick_records_checkpoint_and_replays(tmp_path: Path):
    recovery = Phase0RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "crr"}, source="timer")

    assert loop.run_once(poll_timeout=0.0) == "recovery"

    events = list(loop.bus.read_all())
    event_types = [event["type"] for event in events]
    assert "CRR_TRIGGER_DECIDED" in event_types
    assert "CRR_RECOVERY_STATE_TRANSITION" in event_types
    assert "CRR_CHECKPOINT_RECORDED" in event_types
    assert "CRR_HYGIENE_DELEGATED" in event_types
    assert "CRR_REHYDRATION_VERIFIED" in event_types
    assert "CRR_TRUSTED_SNAPSHOT_RECORDED" in event_types
    assert "CRR_CYCLE_RECORDED" in event_types
    assert "RECOVERY_STATE_CHANGED" in event_types
    assert recovery.last_manifest is not None
    assert verify_checkpoint_manifest(recovery.last_manifest) is True
    evidence_heads = recovery.last_manifest["evidence_chain_heads"]
    assert evidence_heads["rtc_event_log"].startswith("sha256:")
    assert evidence_heads["rtc_event_log"] != "rtc-head-recorded-by-runtime"
    assert evidence_heads["rtc_event_seq"] >= 1
    assert list((tmp_path / "checkpoints").glob("*/manifest.json"))

    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["crr"]["cycles"] == 1
    assert result.state["self"]["ticks"] == 1


def test_crr_panic_preempts_before_recovery_cycle(tmp_path: Path):
    recovery = Phase0RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    loop.panic.enter("test")
    loop.bus.submit("TIMER_EVENT", {"timer_id": "crr"}, source="timer")

    assert loop.run_once(poll_timeout=0.0) == "panic"
    assert recovery.safe_state is True
    assert not list((tmp_path / "checkpoints").glob("*/manifest.json"))


def test_crr_safe_mode_preempts_before_recovery_cycle(tmp_path: Path):
    recovery = Phase0RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    recovery.enter_safe_state()
    loop.bus.submit("TIMER_EVENT", {"timer_id": "crr"}, source="timer")

    assert loop.run_once(poll_timeout=0.0) == "tick"
    assert recovery.safe_state is True
    assert recovery.cycles == 0
    assert not list((tmp_path / "checkpoints").glob("*/manifest.json"))
