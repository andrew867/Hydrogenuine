"""CDO integration and RTC tests — FULL BUILD."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.compromised_disconnected_operation.replay_audit import audit_cdo_events
from hg_runtime.compromised_disconnected_operation.service import FIXTURE_CLOCK, process_signal
from hg_runtime.compromised_disconnected_operation.types import TrustSignal


@pytest.fixture
def cdo_bus(tmp_path: Path) -> EventBus:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    return EventBus(runtime)


def test_full_pipeline_selects_narrowed_posture(monkeypatch: pytest.MonkeyPatch, cdo_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CDO_ENABLED", "1")
    signal = TrustSignal(
        signal_id="sig-full",
        kind="disconnection",
        content_ref="sha256:sig-full",
        observed_at=FIXTURE_CLOCK,
    )
    result = process_signal(
        signal,
        text_hint="network down fully disconnected offline",
        bus=cdo_bus,
    )
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
    assert result["classified_posture"] == "fully_disconnected"
    assert result["emitted_count"] >= 4
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["external_action_recommended"] is False


def test_stale_operator_emits_refusal(monkeypatch: pytest.MonkeyPatch, cdo_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CDO_ENABLED", "1")
    signal = TrustSignal(
        signal_id="sig-stale",
        kind="disconnection",
        content_ref="sha256:sig-stale",
        observed_at=FIXTURE_CLOCK,
        operator_channel_fresh=False,
    )
    result = process_signal(
        signal,
        text_hint="stale operator channel stale",
        bus=cdo_bus,
    )
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["posture"] == "operator_channel_stale"
    assert result["permission_granted"] is False
    assert result["emitted_count"] >= 3


def test_local_replay_only_no_external_action(monkeypatch: pytest.MonkeyPatch, cdo_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CDO_ENABLED", "1")
    signal = TrustSignal(
        signal_id="sig-replay",
        kind="disconnection",
        content_ref="sha256:sig-replay",
        observed_at=FIXTURE_CLOCK,
    )
    result = process_signal(
        signal,
        text_hint="local replay only replay proof only",
        bus=cdo_bus,
    )
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["local_replay_only"] is True
    assert evaluation["external_action_recommended"] is False


def test_unknown_fails_to_safe_mode(monkeypatch: pytest.MonkeyPatch, cdo_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CDO_ENABLED", "1")
    signal = TrustSignal(
        signal_id="sig-unk",
        kind="compromise",
        content_ref="sha256:sig-unk",
        observed_at=FIXTURE_CLOCK,
    )
    result = process_signal(signal, text_hint="unknown", bus=cdo_bus)
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["posture"] == "safe_mode"


def test_posture_not_permission(monkeypatch: pytest.MonkeyPatch, cdo_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CDO_ENABLED", "1")
    signal = TrustSignal(
        signal_id="sig-expand",
        kind="disconnection",
        content_ref="sha256:sig-expand",
        observed_at=FIXTURE_CLOCK,
    )
    result = process_signal(
        signal,
        text_hint="expand authority because disconnected",
        bus=cdo_bus,
    )
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["advisory_only"] is True
    assert evaluation["permission_granted"] is False
    assert result["permission_granted"] is False


def test_disabled_by_default_no_emit(monkeypatch: pytest.MonkeyPatch, cdo_bus: EventBus) -> None:
    monkeypatch.delenv("HG_CDO_ENABLED", raising=False)
    signal = TrustSignal(
        signal_id="sig-off",
        kind="disconnection",
        content_ref="sha256:sig-off",
        observed_at=FIXTURE_CLOCK,
    )
    result = process_signal(signal, text_hint="network down offline", bus=cdo_bus)
    assert result["status"] == "disabled"
    assert result.get("emitted_count", 0) == 0


def test_replay_audit_classifies_cdo_events(monkeypatch: pytest.MonkeyPatch, cdo_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CDO_ENABLED", "1")
    signal = TrustSignal(
        signal_id="sig-audit",
        kind="disconnection",
        content_ref="sha256:sig-audit",
        observed_at=FIXTURE_CLOCK,
    )
    process_signal(signal, text_hint="network down offline", bus=cdo_bus)
    segments = list(cdo_bus.root.glob("events-*.jsonl"))
    assert segments
    report = audit_cdo_events(segments)
    assert report["matched_events"] >= 1
    assert report["permission_granted"] is False


def test_signal_refs_never_include_secrets(monkeypatch: pytest.MonkeyPatch, cdo_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CDO_ENABLED", "1")
    secret_body = "password=supersecret api_key=leaked"
    signal = TrustSignal(
        signal_id="sig-redact",
        kind="compromise",
        content_ref="sha256:sig-redact",
        observed_at=FIXTURE_CLOCK,
    )
    process_signal(signal, text_hint=secret_body, bus=cdo_bus)
    for path in cdo_bus.root.glob("events-*.jsonl"):
        text = path.read_text(encoding="utf-8")
        assert "supersecret" not in text
        assert "password=" not in text
        assert "api_key=" not in text
