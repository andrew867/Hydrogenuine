"""AID integration and RTC tests — FULL BUILD."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.ai_interaction_disclosure.replay_audit import audit_aid_events
from hg_runtime.ai_interaction_disclosure.service import FIXTURE_CLOCK, process_disclosure
from hg_runtime.bus import EventBus

FIXTURE = {
    "disclosure_id": "aid-int-1",
    "runtime_mode": "proposal_only",
    "model_or_provider_label": "fixture-model",
    "capability_claim": "can summarize documents",
    "capability_evidence_ref": "docs/proofs/connective_tissue/CT-A/20260613T005812Z/gate_result.json",
    "content_generated_status": "none",
    "uncertainty_summary": "fixture_slice",
    "known_limitations": "offline_fixture",
}


@pytest.fixture
def aid_bus(tmp_path: Path) -> EventBus:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    return EventBus(runtime)


def test_full_pipeline_records_disclosure_and_mode_card(monkeypatch: pytest.MonkeyPatch, aid_bus: EventBus) -> None:
    monkeypatch.setenv("HG_AID_ENABLED", "1")
    result = process_disclosure(FIXTURE, bus=aid_bus)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False
    assert result["emitted_count"] >= 5
    disclosure = result.get("disclosure")
    assert isinstance(disclosure, dict)
    assert disclosure["is_ai_interaction"] is True
    assert disclosure["proposal_only_status"] is True


def test_syn_feed_present_updates_generated_content(monkeypatch: pytest.MonkeyPatch, aid_bus: EventBus) -> None:
    monkeypatch.setenv("HG_AID_ENABLED", "1")
    syn_feed = {
        "artifact_id": "art-syn-1",
        "content_generated_status": "present",
    }
    result = process_disclosure(FIXTURE, syn_feed=syn_feed, bus=aid_bus)
    generated = result.get("generated_content")
    assert isinstance(generated, dict)
    assert generated["syn_feed_status"] == "present"
    assert generated["content_generated_status"] == "present"


def test_trl_sab_feeds_update_uncertainty(monkeypatch: pytest.MonkeyPatch, aid_bus: EventBus) -> None:
    monkeypatch.setenv("HG_AID_ENABLED", "1")
    trl_feed = {"uncertainty_summary": "trl_unknowns", "known_limitations": "model_limits"}
    sab_feed = {"uncertainty_summary": "sab_unknowns", "known_limitations": "data_gaps"}
    result = process_disclosure(FIXTURE, trl_feed=trl_feed, sab_feed=sab_feed, bus=aid_bus)
    uncertainty = result.get("uncertainty")
    assert isinstance(uncertainty, dict)
    assert uncertainty["trl_feed_status"] == "present"
    assert uncertainty["sab_feed_status"] == "present"
    assert "trl_unknowns" in uncertainty["uncertainty_summary"]


def test_absent_feeds_disclosed(monkeypatch: pytest.MonkeyPatch, aid_bus: EventBus) -> None:
    monkeypatch.setenv("HG_AID_ENABLED", "1")
    result = process_disclosure(FIXTURE, bus=aid_bus)
    uncertainty = result.get("uncertainty")
    generated = result.get("generated_content")
    assert isinstance(uncertainty, dict)
    assert uncertainty["trl_feed_status"] == "absent"
    assert uncertainty["sab_feed_status"] == "absent"
    assert isinstance(generated, dict)
    assert generated["syn_feed_status"] == "absent"


def test_disabled_by_default_no_emit(monkeypatch: pytest.MonkeyPatch, aid_bus: EventBus) -> None:
    monkeypatch.delenv("HG_AID_ENABLED", raising=False)
    result = process_disclosure(FIXTURE, bus=aid_bus)
    assert result["status"] == "disabled"
    assert result.get("emitted_count", 0) == 0


def test_replay_audit_classifies_aid_events(monkeypatch: pytest.MonkeyPatch, aid_bus: EventBus) -> None:
    monkeypatch.setenv("HG_AID_ENABLED", "1")
    process_disclosure(FIXTURE, bus=aid_bus)
    segments = list(aid_bus.root.glob("events-*.jsonl"))
    assert segments
    report = audit_aid_events(segments)
    assert report["matched_events"] >= 1
    assert report["permission_granted"] is False


def test_no_secrets_in_event_payloads(monkeypatch: pytest.MonkeyPatch, aid_bus: EventBus) -> None:
    monkeypatch.setenv("HG_AID_ENABLED", "1")
    secret_fixture = {
        **FIXTURE,
        "disclosure_id": "aid-secret",
        "model_or_provider_label": "sk-live-supersecret-key",
    }
    process_disclosure(secret_fixture, bus=aid_bus)
    for path in aid_bus.root.glob("events-*.jsonl"):
        text = path.read_text(encoding="utf-8")
        assert "sk-live-supersecret-key" not in text


def test_unproven_capability_refused_emits_signal(monkeypatch: pytest.MonkeyPatch, aid_bus: EventBus) -> None:
    monkeypatch.setenv("HG_AID_ENABLED", "1")
    bad = {**FIXTURE, "disclosure_id": "aid-bad", "capability_evidence_ref": ""}
    result = process_disclosure(bad, bus=aid_bus)
    assert result["status"] == "refused"
    assert result["permission_granted"] is False
