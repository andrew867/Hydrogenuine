"""RTC Phase 1 memory integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.handlers import Phase1HALDecisionHandler, Phase1MemoryHandler, StubCognitionHandler
from hg_runtime.handlers.stubs import StubArousalReader, StubKernelHandler, StubRecoveryHandler
from hg_runtime.loop import RuntimeLoop
from hg_runtime.memory.store import index_path, memory_enabled
from hg_runtime.memory.types import redact_mapping
from hg_runtime.replay import replay
from hg_runtime import world_state as ws


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T18:00:{counter['value']:02d}.000000Z"

    return tick


def test_memory_retrieve_store_emits_lifecycle_events(tmp_path: Path):
    handler = Phase1MemoryHandler(runtime_dir=tmp_path / "runtime")
    loop = RuntimeLoop(
        EventBus(tmp_path / "runtime", clock=_clock()),
        cognition=StubCognitionHandler(),
        decision=Phase1HALDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=handler,
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s_mem", "role": "user", "content": "hello"},
        source="plt.chat",
    )
    loop.run_once(poll_timeout=0.0)
    types = [event["type"] for event in loop.bus.read_all()]
    assert "MEMORY_RETRIEVE_REQUESTED" in types
    assert "MEMORY_RETRIEVE_COMPLETED" in types
    assert "MEMORY_RETRIEVED" in types
    assert "MEMORY_STORE_REQUESTED" in types
    assert "MEMORY_STORE_COMPLETED" in types
    assert "MEMORY_WRITTEN" in types
    assert types.index("MEMORY_RETRIEVE_REQUESTED") < types.index("PROPOSAL_EMITTED")
    assert types.index("EFFECT_RECEIPTED") < types.index("MEMORY_STORE_REQUESTED")
    assert index_path(tmp_path / "runtime").exists()
    assert replay(tmp_path / "runtime").ok is True


def test_memory_disabled_emits_explicit_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HG_RTC_MEMORY_ENABLED", "0")
    handler = Phase1MemoryHandler(runtime_dir=tmp_path / "runtime")
    result = handler.retrieve({}, [])
    assert result["context"]["mode"] == "memory_disabled"
    drafts = result["drafts"]
    assert any(d["type"] == "MEMORY_RETRIEVE_REQUESTED" for d in drafts)
    assert any(d["type"] == "MEMORY_RETRIEVE_COMPLETED" for d in drafts)
    store_drafts = handler.store([], [], [])
    assert any(d["type"] == "MEMORY_STORE_COMPLETED" for d in store_drafts)
    assert not index_path(tmp_path / "runtime").exists()


def test_memory_retrieve_context_has_no_authority_fields(tmp_path: Path):
    handler = Phase1MemoryHandler(runtime_dir=tmp_path / "runtime")
    retrieval = handler.retrieve({"activity": {}, "self": {"ticks": 0}}, [])
    context = retrieval["context"]
    forbidden = {"permit", "verdict", "approve", "grant", "capability_id", "authority_ref"}
    assert forbidden.isdisjoint(set(context.keys()))
    for key in context:
        assert "permit" not in str(key).lower()


def test_memory_redacts_secrets():
    payload = redact_mapping({"api_key": "secret", "note": "ok"})
    assert payload["api_key"] == "[REDACTED]"
    assert payload["note"] == "ok"


def test_memory_events_reduce_deterministically(tmp_path: Path):
    handler = Phase1MemoryHandler(runtime_dir=tmp_path / "runtime")
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    loop = RuntimeLoop(
        bus,
        cognition=StubCognitionHandler(),
        decision=Phase1HALDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=handler,
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )
    loop.bus.submit("CHAT_MESSAGE", {"session_id": "s1", "role": "user", "content": "x"}, source="plt.chat")
    loop.run_once(poll_timeout=0.0)
    assert loop.state["activity"]["memory"]["retrieved"] >= 1
    assert loop.state["activity"]["memory"]["written"] >= 1
    replay_result = replay(tmp_path / "runtime")
    assert replay_result.ok is True
    assert replay_result.mismatches == []


def test_memory_modules_have_no_execution_imports():
    forbidden = ("PermitBinder", "mint_permit", "hg_ueak", "hg_oea", "run_gc_for_agent", "compact_session")
    for path in Path("hg_runtime/memory").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"


def test_memory_enabled_default():
    assert memory_enabled() is True
