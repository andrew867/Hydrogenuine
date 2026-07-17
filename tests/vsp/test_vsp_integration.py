"""VSP integration and RTC tests — FULL BUILD."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.policy_safety.errors import PolicyValidationError
from hg_runtime.bus import EventBus
from hg_runtime.vulnerable_subject_protection.replay_audit import audit_vsp_events
from hg_runtime.vulnerable_subject_protection.service import FIXTURE_CLOCK, process_signal
from hg_runtime.vulnerable_subject_protection.types import VulnerabilitySignal


@pytest.fixture
def vsp_bus(tmp_path: Path) -> EventBus:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    return EventBus(runtime)


def test_full_pipeline_classifies_minor_and_emits(monkeypatch: pytest.MonkeyPatch, vsp_bus: EventBus) -> None:
    monkeypatch.setenv("HG_VSP_ENABLED", "1")
    signal = VulnerabilitySignal(
        signal_id="sig-full",
        content_ref="sha256:sig-full",
        context_ref="sha256:ctx-full",
        created_at=FIXTURE_CLOCK,
        uncertainty_note="fixture classification is inferred",
    )
    result = process_signal(
        signal,
        text_hint="I am a teenager under 18 asking for help",
        bus=vsp_bus,
    )
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
    assert result["emitted_count"] >= 4
    protection = result.get("protection")
    assert isinstance(protection, dict)
    assert protection["recommendation"] == "caution"
    routing = result.get("routing")
    assert isinstance(routing, dict)
    assert "SEC" in routing["route_targets"]


def test_crisis_adjacent_emits_escalation_hint(monkeypatch: pytest.MonkeyPatch, vsp_bus: EventBus) -> None:
    monkeypatch.setenv("HG_VSP_ENABLED", "1")
    signal = VulnerabilitySignal(
        signal_id="sig-crisis",
        content_ref="sha256:sig-crisis",
        context_ref="sha256:ctx-crisis",
        created_at=FIXTURE_CLOCK,
        uncertainty_note="fixture classification is inferred",
    )
    result = process_signal(
        signal,
        text_hint="I want to hurt myself and am in crisis",
        bus=vsp_bus,
    )
    protection = result.get("protection")
    assert isinstance(protection, dict)
    assert protection["escalation_hint_only"] is True
    assert protection["diagnosis_fields"] is False
    routing = result.get("routing")
    assert isinstance(routing, dict)
    assert "FTX" in routing["route_targets"]


def test_sensitive_data_routes_sec_ret(monkeypatch: pytest.MonkeyPatch, vsp_bus: EventBus) -> None:
    monkeypatch.setenv("HG_VSP_ENABLED", "1")
    signal = VulnerabilitySignal(
        signal_id="sig-sensitive",
        content_ref="sha256:sig-sensitive",
        context_ref="sha256:ctx-sensitive",
        created_at=FIXTURE_CLOCK,
        uncertainty_note="fixture classification is inferred",
    )
    result = process_signal(
        signal,
        text_hint="here is my ssn and medical record",
        bus=vsp_bus,
    )
    routing = result.get("routing")
    assert isinstance(routing, dict)
    assert "SEC" in routing["route_targets"]
    assert "RET" in routing["route_targets"]
    assert result["permission_granted"] is False


def test_persuasion_use_refused(monkeypatch: pytest.MonkeyPatch, vsp_bus: EventBus) -> None:
    monkeypatch.setenv("HG_VSP_ENABLED", "1")
    signal = VulnerabilitySignal(
        signal_id="sig-persuade",
        content_ref="sha256:sig-persuade",
        context_ref="sha256:ctx-persuade",
        created_at=FIXTURE_CLOCK,
        uncertainty_note="fixture classification is inferred",
    )
    with pytest.raises(PolicyValidationError):
        process_signal(
            signal,
            text_hint="general stress",
            consume_vulnerability_for_persuasion=True,
            bus=vsp_bus,
        )


def test_disabled_by_default_no_emit(monkeypatch: pytest.MonkeyPatch, vsp_bus: EventBus) -> None:
    monkeypatch.delenv("HG_VSP_ENABLED", raising=False)
    signal = VulnerabilitySignal(
        signal_id="sig-off",
        content_ref="sha256:sig-off",
        context_ref="sha256:ctx-off",
        created_at=FIXTURE_CLOCK,
        uncertainty_note="fixture classification is inferred",
    )
    result = process_signal(signal, bus=vsp_bus)
    assert result["status"] == "disabled"
    assert result.get("emitted_count", 0) == 0


def test_replay_audit_classifies_vsp_events(monkeypatch: pytest.MonkeyPatch, vsp_bus: EventBus) -> None:
    monkeypatch.setenv("HG_VSP_ENABLED", "1")
    signal = VulnerabilitySignal(
        signal_id="sig-replay",
        content_ref="sha256:sig-replay",
        context_ref="sha256:ctx-replay",
        created_at=FIXTURE_CLOCK,
        uncertainty_note="fixture classification is inferred",
    )
    process_signal(signal, text_hint="teenager under 18", bus=vsp_bus)
    segments = list(vsp_bus.root.glob("events-*.jsonl"))
    assert segments
    report = audit_vsp_events(segments)
    assert report["matched_events"] >= 1
    assert report["permission_granted"] is False


def test_no_raw_sensitive_content_in_event_payloads(monkeypatch: pytest.MonkeyPatch, vsp_bus: EventBus) -> None:
    monkeypatch.setenv("HG_VSP_ENABLED", "1")
    secret_body = "password=supersecret ssn:123-45-6789"
    signal = VulnerabilitySignal(
        signal_id="sig-redact",
        content_ref="sha256:sig-redact",
        context_ref="sha256:ctx-redact",
        created_at=FIXTURE_CLOCK,
        uncertainty_note="fixture classification is inferred",
    )
    process_signal(signal, text_hint=secret_body, bus=vsp_bus)
    for path in vsp_bus.root.glob("events-*.jsonl"):
        text = path.read_text(encoding="utf-8")
        assert "supersecret" not in text
        assert "password=" not in text
        assert "123-45-6789" not in text
