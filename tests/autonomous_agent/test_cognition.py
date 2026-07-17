"""Cognition package tests — config, provider, fake provider, streaming.

Coverage for the second-highest-risk untested package (9 downstream importers).
Fixture-only: PROVIDER_MODE = FIXTURE_ONLY_PROVIDER_DISABLED.
"""

from __future__ import annotations

import time

import pytest

from hg_runtime.cognition.config import (
    CognitionConfig,
    LiveCognitionConfigError,
    load_cognition_config,
    validate_live_config,
)
from hg_runtime.cognition.provider import (
    CognitionCancelled,
    CognitionPrompt,
    CognitionTimeout,
    build_provider,
)
from hg_runtime.cognition.fake_provider import (
    FailingModelProvider,
    FakeModelProvider,
)

PROVIDER_MODE = "FIXTURE_ONLY_PROVIDER_DISABLED"


def _make_prompt(trigger_type: str = "test") -> CognitionPrompt:
    return CognitionPrompt(
        messages=({"role": "user", "content": "test"},),
        trigger_event_id="evt-001",
        trigger_type=trigger_type,
        request_digest="digest-001",
    )


class TestCognitionConfig:
    def test_default_config_is_fake_offline(self):
        config = CognitionConfig()
        assert config.provider == "fake"
        assert config.offline is True
        assert config.uses_live_model is False

    def test_live_model_detection(self):
        config = CognitionConfig(provider="openai", model="gpt-4o", live_enabled=True, offline=False)
        assert config.uses_live_model is True

    def test_fake_provider_never_live(self):
        config = CognitionConfig(provider="fake", live_enabled=True, offline=False)
        assert config.uses_live_model is False

    def test_load_config_defaults(self, monkeypatch):
        monkeypatch.delenv("HG_RTC_COGNITION_PROVIDER", raising=False)
        monkeypatch.delenv("HG_RTC_COGNITION_MODEL", raising=False)
        monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
        config = load_cognition_config()
        assert config.provider == "fake"
        assert config.offline is True


class TestValidateLiveConfig:
    def test_offline_config_skips_validation(self):
        config = CognitionConfig(provider="fake", offline=True)
        validate_live_config(config)

    def test_live_openai_without_key_raises(self):
        config = CognitionConfig(
            provider="openai", model="gpt-4o", live_enabled=True, offline=False, api_key=None,
        )
        with pytest.raises(LiveCognitionConfigError):
            validate_live_config(config)

    def test_live_vllm_without_base_url_raises(self):
        config = CognitionConfig(
            provider="vllm", model="llama", live_enabled=True, offline=False, base_url=None,
        )
        with pytest.raises(LiveCognitionConfigError):
            validate_live_config(config)

    def test_live_unsupported_provider_raises(self):
        config = CognitionConfig(
            provider="anthropic", model="claude", live_enabled=True, offline=False,
        )
        with pytest.raises(LiveCognitionConfigError):
            validate_live_config(config)

    def test_live_openai_without_model_raises(self):
        config = CognitionConfig(
            provider="openai", model="", live_enabled=True, offline=False, api_key="sk-test",
        )
        with pytest.raises(LiveCognitionConfigError):
            validate_live_config(config)


class TestBuildProvider:
    def test_build_fake_provider(self):
        config = CognitionConfig(provider="fake", model="test-model")
        provider = build_provider(config)
        assert isinstance(provider, FakeModelProvider)
        assert provider.model_name == "test-model"

    def test_build_offline_openai_returns_fake(self):
        config = CognitionConfig(provider="openai", model="gpt-4o", offline=True)
        provider = build_provider(config)
        assert isinstance(provider, FakeModelProvider)
        assert "offline:" in provider.model_name

    def test_build_unsupported_raises(self):
        config = CognitionConfig(provider="anthropic", model="claude", offline=True)
        with pytest.raises(ValueError, match="unsupported"):
            build_provider(config)


class TestFakeModelProvider:
    def test_streams_valid_json(self):
        provider = FakeModelProvider(model_name="test")
        prompt = _make_prompt("decision")
        tokens = list(provider.stream_tokens(
            prompt, cancel_check=lambda: False, deadline_monotonic=time.monotonic() + 10,
        ))
        text = "".join(tokens)
        import json
        payload = json.loads(text)
        assert payload["kind"] == "candidate_action"
        assert "acknowledge" in payload["content"]["summary"]

    def test_cancel_raises(self):
        provider = FakeModelProvider(model_name="test")
        prompt = _make_prompt()
        with pytest.raises(CognitionCancelled):
            list(provider.stream_tokens(
                prompt, cancel_check=lambda: True, deadline_monotonic=time.monotonic() + 10,
            ))

    def test_timeout_raises(self):
        provider = FakeModelProvider(model_name="test")
        prompt = _make_prompt()
        with pytest.raises(CognitionTimeout):
            list(provider.stream_tokens(
                prompt, cancel_check=lambda: False, deadline_monotonic=time.monotonic() - 1,
            ))

    def test_provider_id(self):
        provider = FakeModelProvider()
        assert provider.provider_id == "fake"


class TestFailingModelProvider:
    def test_raises_on_stream(self):
        provider = FailingModelProvider()
        prompt = _make_prompt()
        with pytest.raises(RuntimeError, match="provider unavailable"):
            list(provider.stream_tokens(
                prompt, cancel_check=lambda: False, deadline_monotonic=time.monotonic() + 10,
            ))

    def test_provider_id(self):
        provider = FailingModelProvider()
        assert provider.provider_id == "failing"


class TestCognitionPrompt:
    def test_prompt_is_frozen(self):
        prompt = _make_prompt("test")
        assert prompt.trigger_type == "test"
        with pytest.raises(AttributeError):
            prompt.trigger_type = "modified"

    def test_prompt_fields(self):
        prompt = _make_prompt("decision")
        assert prompt.trigger_event_id == "evt-001"
        assert prompt.request_digest == "digest-001"
        assert len(prompt.messages) == 1
