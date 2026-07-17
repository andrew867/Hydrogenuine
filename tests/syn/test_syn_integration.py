"""SYN integration and RTC tests — FULL BUILD."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.synthetic_content_provenance.replay_audit import audit_syn_events
from hg_runtime.synthetic_content_provenance.service import process_artifact
from hg_runtime.synthetic_content_provenance.types import SyntheticContentArtifact

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


@pytest.fixture
def syn_bus(tmp_path: Path) -> EventBus:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    return EventBus(runtime)


def test_full_pipeline_records_provenance_and_label(monkeypatch: pytest.MonkeyPatch, syn_bus: EventBus) -> None:
    monkeypatch.setenv("HG_SYN_ENABLED", "1")
    artifact = SyntheticContentArtifact(
        artifact_id="art-full",
        content_class="text",
        content_ref="sha256:art-full",
        generated=True,
        created_at=FIXTURE_CLOCK,
    )
    result = process_artifact(artifact, text_hint="generated summary", bus=syn_bus)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
    assert result["emitted_count"] >= 5
    assert result.get("receipt") is not None


def test_watermark_metadata_not_safety_proof(monkeypatch: pytest.MonkeyPatch, syn_bus: EventBus) -> None:
    monkeypatch.setenv("HG_SYN_ENABLED", "1")
    artifact = SyntheticContentArtifact(
        artifact_id="art-wm",
        content_class="image",
        content_ref="sha256:art-wm",
        generated=True,
        created_at=FIXTURE_CLOCK,
    )
    result = process_artifact(artifact, text_hint="synthetic person media", bus=syn_bus)
    wm = result.get("watermark")
    assert isinstance(wm, dict)
    assert wm.get("is_safety_proof") is False
    assert "safe" not in wm


def test_export_receipt_includes_artifact_hash(monkeypatch: pytest.MonkeyPatch, syn_bus: EventBus) -> None:
    monkeypatch.setenv("HG_SYN_ENABLED", "1")
    artifact = SyntheticContentArtifact(
        artifact_id="art-exp",
        content_class="text",
        content_ref="sha256:art-exp",
        generated=True,
        created_at=FIXTURE_CLOCK,
    )
    result = process_artifact(artifact, text_hint="generated summary for operator", bus=syn_bus)
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    assert receipt["artifact_hash"] == artifact.record_hash
    assert receipt.get("export_is_not_permission") is True


def test_disabled_by_default_no_emit(monkeypatch: pytest.MonkeyPatch, syn_bus: EventBus) -> None:
    monkeypatch.delenv("HG_SYN_ENABLED", raising=False)
    artifact = SyntheticContentArtifact(
        artifact_id="art-off",
        content_class="text",
        content_ref="sha256:art-off",
        generated=True,
        created_at=FIXTURE_CLOCK,
    )
    result = process_artifact(artifact, bus=syn_bus)
    assert result["status"] == "disabled"
    assert result.get("emitted_count", 0) == 0


def test_replay_audit_classifies_syn_events(monkeypatch: pytest.MonkeyPatch, syn_bus: EventBus) -> None:
    monkeypatch.setenv("HG_SYN_ENABLED", "1")
    artifact = SyntheticContentArtifact(
        artifact_id="art-replay",
        content_class="text",
        content_ref="sha256:art-replay",
        generated=True,
        created_at=FIXTURE_CLOCK,
    )
    process_artifact(artifact, text_hint="generated", bus=syn_bus)
    segments = list(syn_bus.root.glob("events-*.jsonl"))
    assert segments
    report = audit_syn_events(segments)
    assert report["matched_events"] >= 1
    assert report["permission_granted"] is False


def test_artifact_contents_never_in_event_payloads(monkeypatch: pytest.MonkeyPatch, syn_bus: EventBus) -> None:
    monkeypatch.setenv("HG_SYN_ENABLED", "1")
    secret_body = "password=supersecret"
    artifact = SyntheticContentArtifact(
        artifact_id="art-redact",
        content_class="text",
        content_ref="sha256:art-redact",
        generated=True,
        created_at=FIXTURE_CLOCK,
    )
    process_artifact(artifact, text_hint=secret_body, bus=syn_bus)
    for path in syn_bus.root.glob("events-*.jsonl"):
        text = path.read_text(encoding="utf-8")
        assert "supersecret" not in text
        assert "password=" not in text
