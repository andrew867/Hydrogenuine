"""CRT integration and RTC tests — FULL BUILD."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.certification_evidence_pack.replay_audit import audit_crt_events
from hg_runtime.certification_evidence_pack.service import FIXTURE_CLOCK, process_certification_export

HEAD = "4a2bf6c2075c262f9436586c384f47b5b1b2977e"
EVIDENCE_REF = "ev-p1a-proof"
EVIDENCE_HASH = "sha256:047526882c13a00c984eac013102b5ce2d9634192bdac1f0986c9c5092260ca1"


def _sample_fixtures() -> dict[str, list[dict[str, str]]]:
    return {
        "claims": [
            {
                "claim_id": "claim-supported",
                "statement": "P1-A policy batch gate green",
                "control_domain": "testing",
                "status": "supported",
                "evidence_refs": EVIDENCE_REF,
            },
            {
                "claim_id": "claim-unsupported",
                "statement": "live runtime orchestration green",
                "control_domain": "automation_limits",
                "status": "unsupported",
            },
        ],
        "exceptions": [
            {
                "exception_id": "exc-rtc",
                "detail": "RTC policy_safety events deferred to post-P1",
                "control_domain": "logging",
            }
        ],
        "evidence_refs": [
            {
                "evidence_id": EVIDENCE_REF,
                "path": "docs/proofs/policy_safety/P1-A/all/20260613T012632Z",
                "content_hash": EVIDENCE_HASH,
                "fresh": "true",
            },
            {
                "evidence_id": "ev-stale",
                "path": "docs/proofs/connective_tissue/CT-A/20260613T005812Z",
                "content_hash": "sha256:deadbeef",
                "fresh": "false",
            },
        ],
    }


@pytest.fixture
def crt_bus(tmp_path: Path) -> EventBus:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    return EventBus(runtime)


def test_full_pipeline_creates_export_and_emits(monkeypatch: pytest.MonkeyPatch, crt_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CRT_ENABLED", "1")
    fixtures = _sample_fixtures()
    result = process_certification_export(
        snapshot_id="snap-full",
        branch="main",
        head=HEAD,
        claims=fixtures["claims"],
        exceptions=fixtures["exceptions"],
        evidence_refs=fixtures["evidence_refs"],
        bus=crt_bus,
        observed_at=FIXTURE_CLOCK,
    )
    assert result["status"] == "exported"
    assert result["permission_granted"] is False
    assert result["certification_granted"] is False
    assert result["emitted_count"] >= 5
    export = result.get("export")
    assert isinstance(export, dict)
    assert export.get("certification_granted") is False


def test_export_not_certification(monkeypatch: pytest.MonkeyPatch, crt_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CRT_ENABLED", "1")
    fixtures = _sample_fixtures()
    result = process_certification_export(
        snapshot_id="snap-not-cert",
        branch="main",
        head=HEAD,
        claims=fixtures["claims"],
        exceptions=fixtures["exceptions"],
        evidence_refs=fixtures["evidence_refs"],
        bus=crt_bus,
    )
    export = result.get("export")
    assert isinstance(export, dict)
    assert export["permission_granted"] is False
    assert export["certification_granted"] is False
    assert "certification evidence is not certification" in export.get("detail", "")


def test_exceptions_always_in_export(monkeypatch: pytest.MonkeyPatch, crt_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CRT_ENABLED", "1")
    fixtures = _sample_fixtures()
    result = process_certification_export(
        snapshot_id="snap-exc",
        branch="main",
        head=HEAD,
        claims=fixtures["claims"],
        exceptions=fixtures["exceptions"],
        evidence_refs=fixtures["evidence_refs"],
        bus=crt_bus,
    )
    assert result["exception_count"] == 1
    export = result.get("export")
    assert isinstance(export, dict)
    assert len(export["snapshot"]["exceptions"]) == 1


def test_exception_suppression_refused(monkeypatch: pytest.MonkeyPatch, crt_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CRT_ENABLED", "1")
    fixtures = _sample_fixtures()
    result = process_certification_export(
        snapshot_id="snap-suppress",
        branch="main",
        head=HEAD,
        claims=fixtures["claims"],
        exceptions=fixtures["exceptions"],
        evidence_refs=fixtures["evidence_refs"],
        bus=crt_bus,
        suppress_exceptions=True,
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == "crt.refused.exception_suppression"


def test_disabled_by_default_no_emit(monkeypatch: pytest.MonkeyPatch, crt_bus: EventBus) -> None:
    monkeypatch.delenv("HG_CRT_ENABLED", raising=False)
    fixtures = _sample_fixtures()
    result = process_certification_export(
        snapshot_id="snap-off",
        branch="main",
        head=HEAD,
        claims=fixtures["claims"],
        exceptions=fixtures["exceptions"],
        evidence_refs=fixtures["evidence_refs"],
        bus=crt_bus,
    )
    assert result["status"] == "disabled"
    assert result.get("emitted_count", 0) == 0


def test_replay_audit_classifies_crt_events(monkeypatch: pytest.MonkeyPatch, crt_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CRT_ENABLED", "1")
    fixtures = _sample_fixtures()
    process_certification_export(
        snapshot_id="snap-replay",
        branch="main",
        head=HEAD,
        claims=fixtures["claims"],
        exceptions=fixtures["exceptions"],
        evidence_refs=fixtures["evidence_refs"],
        bus=crt_bus,
    )
    segments = list(crt_bus.root.glob("events-*.jsonl"))
    assert segments
    report = audit_crt_events(segments)
    assert report["matched_events"] >= 1
    assert report["permission_granted"] is False


def test_secrets_never_in_event_payloads(monkeypatch: pytest.MonkeyPatch, crt_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CRT_ENABLED", "1")
    secret = "api_key=supersecret"
    fixtures = _sample_fixtures()
    fixtures["claims"][0]["statement"] = secret
    process_certification_export(
        snapshot_id="snap-redact",
        branch="main",
        head=HEAD,
        claims=fixtures["claims"],
        exceptions=fixtures["exceptions"],
        evidence_refs=fixtures["evidence_refs"],
        bus=crt_bus,
    )
    for path in crt_bus.root.glob("events-*.jsonl"):
        text = path.read_text(encoding="utf-8")
        assert "supersecret" not in text
        assert "api_key=" not in text


def test_fake_green_refused_with_rtc(monkeypatch: pytest.MonkeyPatch, crt_bus: EventBus) -> None:
    monkeypatch.setenv("HG_CRT_ENABLED", "1")
    result = process_certification_export(
        snapshot_id="snap-fake",
        branch="main",
        head=HEAD,
        claims=[
            {
                "claim_id": "claim-fake",
                "statement": "everything production ready",
                "control_domain": "testing",
                "status": "supported",
            }
        ],
        exceptions=[],
        evidence_refs=[],
        bus=crt_bus,
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == "crt.refused.fake_green_prevented"
