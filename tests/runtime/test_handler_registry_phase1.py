"""Handler registry Phase 1 integration defaults."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hg_runtime.handlers import HandlerRegistry, StreamingCognitionHandler, StubCognitionHandler
from hg_runtime.handlers.aep_arousal import Phase1AEPArousalHandler
from hg_runtime.handlers.hal_decision import Phase1HALDecisionHandler
from hg_runtime.handlers.stubs import StubArousalReader, StubDecisionHandler


def test_phase0_stubs_unchanged():
    reg = HandlerRegistry.phase0_stubs()
    assert isinstance(reg.cognition, StubCognitionHandler)
    assert isinstance(reg.decision, StubDecisionHandler)
    assert isinstance(reg.arousal, StubArousalReader)


def test_phase1_integrated_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HG_RTC_COGNITION_STREAMING", raising=False)
    monkeypatch.setenv("HG_RTC_AEP_PROCESSOR", "1")
    monkeypatch.setenv("HG_GPP_PERMIT_BIND", "1")
    reg = HandlerRegistry.phase1_integrated(runtime_dir=tmp_path / "rtc")
    assert isinstance(reg.arousal, Phase1AEPArousalHandler)
    assert isinstance(reg.decision, Phase1HALDecisionHandler)
    assert isinstance(reg.cognition, StubCognitionHandler)


def test_streaming_enabled_by_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HG_RTC_COGNITION_STREAMING", "1")
    monkeypatch.setenv("HG_RTC_COGNITION_PROVIDER", "fake")
    reg = HandlerRegistry.phase1_integrated(runtime_dir=Path(".tmp/rtc"))
    assert isinstance(reg.cognition, StreamingCognitionHandler)


def test_build_from_env_respects_handler_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HG_RTC_HANDLER_MODE", "phase0")
    reg = HandlerRegistry.build_from_env()
    assert isinstance(reg.cognition, StubCognitionHandler)
