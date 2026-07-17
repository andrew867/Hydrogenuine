"""DMI integration and RTC tests — FULL BUILD."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.democratic_misinformation_integrity.replay_audit import audit_dmi_events
from hg_runtime.democratic_misinformation_integrity.service import FIXTURE_CLOCK, process_signal
from hg_runtime.democratic_misinformation_integrity.types import PublicInfluenceSignal


@pytest.fixture
def dmi_bus(tmp_path: Path) -> EventBus:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    return EventBus(runtime)


def test_full_pipeline_classifies_election_and_review(monkeypatch: pytest.MonkeyPatch, dmi_bus: EventBus) -> None:
    monkeypatch.setenv("HG_DMI_ENABLED", "1")
    signal = PublicInfluenceSignal(
        signal_id="sig-full",
        content_ref="sha256:sig-full",
        channel="fixture",
        created_at=FIXTURE_CLOCK,
    )
    result = process_signal(
        signal,
        text_hint="Vote for candidate X in the upcoming election",
        disclosure_present=True,
        evidence_refs=("sha256:evidence",),
        bus=dmi_bus,
    )
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
    assert result["emitted_count"] >= 3
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["recommendation"] == "review"


def test_institutional_impersonation_refused(monkeypatch: pytest.MonkeyPatch, dmi_bus: EventBus) -> None:
    monkeypatch.setenv("HG_DMI_ENABLED", "1")
    signal = PublicInfluenceSignal(
        signal_id="sig-inst",
        content_ref="sha256:sig-inst",
        channel="fixture",
        created_at=FIXTURE_CLOCK,
    )
    result = process_signal(
        signal,
        text_hint="SEC press office announcement on enforcement",
        disclosure_present=True,
        evidence_refs=("sha256:ev",),
        bus=dmi_bus,
    )
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["recommendation"] == "refuse"
    assert result["permission_granted"] is False


def test_persuasion_optimization_refused(monkeypatch: pytest.MonkeyPatch, dmi_bus: EventBus) -> None:
    monkeypatch.setenv("HG_DMI_ENABLED", "1")
    signal = PublicInfluenceSignal(
        signal_id="sig-opt",
        content_ref="sha256:sig-opt",
        channel="fixture",
        created_at=FIXTURE_CLOCK,
    )
    result = process_signal(
        signal,
        text_hint="optimize for swing voters in this district",
        bus=dmi_bus,
    )
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["recommendation"] == "refuse"


def test_recommendation_not_permission(monkeypatch: pytest.MonkeyPatch, dmi_bus: EventBus) -> None:
    monkeypatch.setenv("HG_DMI_ENABLED", "1")
    signal = PublicInfluenceSignal(
        signal_id="sig-adv",
        content_ref="sha256:sig-adv",
        channel="fixture",
        created_at=FIXTURE_CLOCK,
    )
    result = process_signal(
        signal,
        text_hint="civic education summary",
        disclosure_present=True,
        evidence_refs=("sha256:ev",),
        bus=dmi_bus,
    )
    evaluation = result.get("evaluation")
    assert isinstance(evaluation, dict)
    assert evaluation["advisory_only"] is True
    assert evaluation["permission_granted"] is False
    assert result["permission_granted"] is False


def test_disabled_by_default_no_emit(monkeypatch: pytest.MonkeyPatch, dmi_bus: EventBus) -> None:
    monkeypatch.delenv("HG_DMI_ENABLED", raising=False)
    signal = PublicInfluenceSignal(
        signal_id="sig-off",
        content_ref="sha256:sig-off",
        channel="fixture",
        created_at=FIXTURE_CLOCK,
    )
    result = process_signal(signal, text_hint="election ballot info", bus=dmi_bus)
    assert result["status"] == "disabled"
    assert result.get("emitted_count", 0) == 0


def test_replay_audit_classifies_dmi_events(monkeypatch: pytest.MonkeyPatch, dmi_bus: EventBus) -> None:
    monkeypatch.setenv("HG_DMI_ENABLED", "1")
    signal = PublicInfluenceSignal(
        signal_id="sig-replay",
        content_ref="sha256:sig-replay",
        channel="fixture",
        created_at=FIXTURE_CLOCK,
    )
    process_signal(
        signal,
        text_hint="Vote for candidate in election",
        disclosure_present=True,
        evidence_refs=("sha256:ev",),
        bus=dmi_bus,
    )
    segments = list(dmi_bus.root.glob("events-*.jsonl"))
    assert segments
    report = audit_dmi_events(segments)
    assert report["matched_events"] >= 1
    assert report["permission_granted"] is False


def test_content_by_ref_only_never_in_payloads(monkeypatch: pytest.MonkeyPatch, dmi_bus: EventBus) -> None:
    monkeypatch.setenv("HG_DMI_ENABLED", "1")
    secret_body = "password=supersecret ballot manipulation"
    signal = PublicInfluenceSignal(
        signal_id="sig-redact",
        content_ref="sha256:sig-redact",
        channel="fixture",
        created_at=FIXTURE_CLOCK,
    )
    process_signal(signal, text_hint=secret_body, bus=dmi_bus)
    for path in dmi_bus.root.glob("events-*.jsonl"):
        text = path.read_text(encoding="utf-8")
        assert "supersecret" not in text
        assert "password=" not in text
        assert "ballot manipulation" not in text
