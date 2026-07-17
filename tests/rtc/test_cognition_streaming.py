from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.cognition import (
    FakeModelProvider,
    StreamingCognitionHandler,
    build_provider,
    find_recorded_proposal,
    load_cognition_config,
    reconstruct_assembled_text,
)
from hg_runtime.cognition.config import CognitionConfig, LiveCognitionConfigError
from hg_runtime.cognition.fake_provider import FailingModelProvider, FakeModelProvider as FakeProviderClass
from hg_runtime.cognition.provider import CognitionPrompt
from hg_runtime.handlers import (
    StubArousalReader,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
    StubRecoveryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T07:00:{counter['value']:02d}.000000Z"

    return tick


def _loop(tmp_path: Path, cognition: StreamingCognitionHandler) -> RuntimeLoop:
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    return RuntimeLoop(
        bus,
        cognition=cognition,
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )


def test_build_prompt_digest_handles_readonly_memory_context():
    from types import MappingProxyType

    from hg_runtime.cognition.streaming import build_prompt

    prompt = build_prompt(
        {
            "events": [
                {
                    "event_id": "evt_trigger",
                    "type": "CHAT_MESSAGE",
                    "payload": {"content": "hello"},
                }
            ],
            "memory": MappingProxyType({"session": MappingProxyType({"id": "s1"})}),
            "arousal": MappingProxyType({"level": "nominal"}),
        }
    )
    assert prompt.request_digest.startswith("sha256:")


def test_fake_streaming_provider_emits_deterministic_model_token_events():
    provider = FakeModelProvider()
    handler = StreamingCognitionHandler(
        provider=provider,
        config=CognitionConfig(provider="fake", model="rtc-fake-model", timeout_s=5.0),
    )
    drafts = handler.propose(
        {
            "events": [
                {
                    "event_id": "evt_trigger",
                    "type": "CHAT_MESSAGE",
                    "payload": {"content": "hello"},
                }
            ],
            "world_state": {},
            "memory": {},
            "arousal": {},
        }
    )
    types = [draft["type"] for draft in drafts]
    assert types[0] == "MODEL_STREAM_STARTED"
    assert types.count("MODEL_TOKEN_DELTA") > 0
    assert "MODEL_STREAM_COMPLETED" in types
    assert types[-1] == "MODEL_PROPOSAL_RECORDED"
    assert drafts[-1]["payload"]["kind"] == "candidate_action"
    # deterministic: same trigger yields same token count
    drafts_again = handler.propose(
        {
            "events": [
                {
                    "event_id": "evt_trigger",
                    "type": "CHAT_MESSAGE",
                    "payload": {"content": "hello"},
                }
            ],
            "world_state": {},
            "memory": {},
            "arousal": {},
        }
    )
    types_again = [draft["type"] for draft in drafts_again]
    assert types.count("MODEL_TOKEN_DELTA") == types_again.count("MODEL_TOKEN_DELTA")


def test_streaming_cognition_writes_tokens_to_event_log(tmp_path: Path):
    handler = StreamingCognitionHandler(
        provider=FakeModelProvider(),
        config=CognitionConfig(provider="fake"),
    )
    loop = _loop(tmp_path, handler)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "stream me"},
        source="plt.chat",
    )
    assert loop.run_once(poll_timeout=0.0) == "tick"
    types = [event["type"] for event in list(loop.bus.read_all())]
    assert "MODEL_STREAM_STARTED" in types
    assert "MODEL_TOKEN_DELTA" in types
    assert "MODEL_STREAM_COMPLETED" in types
    assert "MODEL_PROPOSAL_RECORDED" in types
    assert types.index("MODEL_STREAM_STARTED") < types.index("MODEL_TOKEN_DELTA")
    assert types.index("MODEL_TOKEN_DELTA") < types.index("MODEL_STREAM_COMPLETED")
    assert types.index("MODEL_STREAM_COMPLETED") < types.index("MODEL_PROPOSAL_RECORDED")
    assert loop.state["activity"]["proposals"]["tokens"] > 0
    assert types.count("DECISION_BLOCKED") == 0
    assert types.count("DECISION_EVENT") == 1


def test_replay_reconstructs_proposal_text_without_calling_model_provider(tmp_path: Path):
    provider = FakeModelProvider()
    handler = StreamingCognitionHandler(provider=provider, config=CognitionConfig(provider="fake"))
    loop = _loop(tmp_path, handler)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "replay"},
        source="plt.chat",
    )
    loop.run_once(poll_timeout=0.0)
    events = list(loop.bus.read_all())
    calls_before = handler.calls
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert handler.calls == calls_before
    assert result.state["activity"]["proposals"]["emitted"] == 1
    assert result.state["activity"]["proposals"]["tokens"] > 0
    assembled = reconstruct_assembled_text(events)
    recorded = find_recorded_proposal(events)
    assert recorded is not None
    assert recorded["payload"]["assembled_text"] == assembled
    assert json.loads(assembled)["kind"] == "candidate_action"


def test_timeout_emits_model_stream_failed_not_handler_failed(tmp_path: Path):
    slow = FakeProviderClass(delay_per_token_s=0.05)
    handler = StreamingCognitionHandler(
        provider=slow,
        config=CognitionConfig(provider="fake", timeout_s=0.01),
    )
    loop = _loop(tmp_path, handler)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "slow"},
        source="plt.chat",
    )
    assert loop.run_once(poll_timeout=0.0) == "tick"
    types = [event["type"] for event in list(loop.bus.read_all())]
    assert "MODEL_STREAM_FAILED" in types
    assert "HANDLER_FAILED" not in types
    assert loop.state["activity"]["proposals"]["failed"] == 1


def test_provider_failure_emits_model_stream_failed(tmp_path: Path):
    handler = StreamingCognitionHandler(
        provider=FailingModelProvider(),
        config=CognitionConfig(provider="fake", timeout_s=5.0),
    )
    loop = _loop(tmp_path, handler)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "fail"},
        source="plt.chat",
    )
    assert loop.run_once(poll_timeout=0.0) == "tick"
    events = list(loop.bus.read_all())
    types = [event["type"] for event in events]
    assert "MODEL_STREAM_STARTED" in types
    assert "MODEL_STREAM_FAILED" in types
    assert "MODEL_PROPOSAL_RECORDED" not in types
    failed = next(event for event in events if event["type"] == "MODEL_STREAM_FAILED")
    assert failed["payload"]["reason"] == "RuntimeError"


def test_halt_emits_cancel_failure_without_corrupting_loop(tmp_path: Path):
    handler = StreamingCognitionHandler(
        provider=FakeProviderClass(delay_per_token_s=0.2),
        config=CognitionConfig(provider="fake", timeout_s=5.0),
    )
    handler.halt()
    loop = _loop(tmp_path, handler)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "halt"},
        source="plt.chat",
    )
    assert loop.run_once(poll_timeout=0.0) == "tick"
    types = [event["type"] for event in list(loop.bus.read_all())]
    assert "MODEL_STREAM_FAILED" in types
    assert replay(tmp_path / "runtime").ok is True


def test_live_provider_skipped_unless_explicitly_configured(monkeypatch):
    monkeypatch.setenv("HG_RTC_COGNITION_PROVIDER", "vllm")
    monkeypatch.setenv("HG_RTC_COGNITION_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
    config = load_cognition_config()
    provider = build_provider(config)
    assert isinstance(provider, FakeModelProvider)
    assert config.offline is True
    assert config.uses_live_model is False


def test_live_config_fails_clearly_without_base_url_for_vllm(monkeypatch):
    monkeypatch.setenv("HG_RTC_COGNITION_PROVIDER", "vllm")
    monkeypatch.setenv("HG_RTC_COGNITION_LIVE", "1")
    monkeypatch.setenv("HG_RTC_COGNITION_OFFLINE", "0")
    monkeypatch.setenv("HG_RTC_COGNITION_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    monkeypatch.delenv("HG_RTC_COGNITION_BASE_URL", raising=False)
    monkeypatch.delenv("HG_VLLM_BASE_URL", raising=False)
    with pytest.raises(LiveCognitionConfigError, match="BASE_URL"):
        load_cognition_config()


def test_live_config_fails_clearly_without_api_key_for_openai(monkeypatch):
    monkeypatch.setenv("HG_RTC_COGNITION_PROVIDER", "openai")
    monkeypatch.setenv("HG_RTC_COGNITION_LIVE", "1")
    monkeypatch.setenv("HG_RTC_COGNITION_OFFLINE", "0")
    monkeypatch.setenv("HG_RTC_COGNITION_MODEL", "gpt-4o-mini")
    monkeypatch.delenv("HG_RTC_COGNITION_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LiveCognitionConfigError, match="API_KEY"):
        load_cognition_config()


def test_live_mode_does_not_silently_fallback_when_misconfigured(monkeypatch):
    monkeypatch.setenv("HG_RTC_COGNITION_PROVIDER", "openai")
    monkeypatch.setenv("HG_RTC_COGNITION_LIVE", "1")
    monkeypatch.setenv("HG_RTC_COGNITION_OFFLINE", "0")
    monkeypatch.setenv("HG_RTC_COGNITION_MODEL", "gpt-4o-mini")
    monkeypatch.delenv("HG_RTC_COGNITION_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LiveCognitionConfigError):
        build_provider(
            CognitionConfig(
                provider="openai",
                model="gpt-4o-mini",
                live_enabled=True,
                offline=False,
                api_key=None,
            )
        )


def test_proposal_event_is_not_direct_action_execution(tmp_path: Path):
    handler = StreamingCognitionHandler(
        provider=FakeModelProvider(),
        config=CognitionConfig(provider="fake"),
    )
    loop = _loop(tmp_path, handler)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "proposal only"},
        source="plt.chat",
    )
    loop.run_once(poll_timeout=0.0)
    events = list(loop.bus.read_all())
    types = [event["type"] for event in events]
    assert "MODEL_PROPOSAL_RECORDED" in types
    assert "OEA_EXECUTION_STARTED" not in types
    assert "OEA_EXECUTION_COMPLETED" not in types
    assert types.count("DECISION_EVENT") == 1


def test_live_gate_refuses_without_live_flag(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
    import scripts.evals.live_cognition_gate as gate

    assert gate.main() == 1


@pytest.mark.skipif(
    os.environ.get("HG_RTC_COGNITION_LIVE") != "1",
    reason="live vLLM/OpenAI provider not enabled (set HG_RTC_COGNITION_LIVE=1)",
)
@pytest.mark.llm_live
def test_live_provider_builds_openai_compatible_adapter(monkeypatch):
    monkeypatch.setenv("HG_RTC_COGNITION_PROVIDER", "vllm")
    monkeypatch.setenv("HG_RTC_COGNITION_LIVE", "1")
    monkeypatch.setenv("HG_RTC_COGNITION_OFFLINE", "0")
    monkeypatch.setenv("HG_RTC_COGNITION_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("HG_RTC_COGNITION_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    config = load_cognition_config()
    provider = build_provider(config)
    from hg_runtime.cognition.openai_provider import OpenAICompatibleProvider

    assert isinstance(provider, OpenAICompatibleProvider)
    assert config.uses_live_model is True


def test_cognition_modules_have_no_tool_handles_or_execution_imports():
    forbidden_prefixes = ("hg_ueak", "hg_oea", "subprocess", "socket", "httpx", "requests")
    for path in Path("hg_runtime/cognition").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        for name in imports:
            assert not any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)
        cognition_class = next(
            (node for node in tree.body if isinstance(node, ast.ClassDef) and "Handler" in node.name),
            None,
        )
        if cognition_class is not None:
            for node in ast.walk(cognition_class):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and "tool" in target.id.lower():
                            raise AssertionError(f"unexpected tool handle {target.id} in {path}")
