"""RES offline evidence record tests."""

from __future__ import annotations

import pytest

from hg_core.runtime_context.errors import RuntimeContextValidationError
from hg_runtime.research_evidence_acquisition.policy import (
    evaluate_research_request,
    refuse_research_as_truth,
)
from hg_runtime.research_evidence_acquisition.records import FIXTURE_CLOCK, record_from_provided_file
from hg_runtime.research_evidence_acquisition.types import EvidenceRecord, request_from_fixture


def test_offline_evidence_record_positive() -> None:
    request = request_from_fixture(
        {
            "request_id": "req-1",
            "acquisition_mode": "provided_files",
            "uncertainty": "bounded",
        }
    )
    evidence = record_from_provided_file(
        {
            "evidence_id": "ev-1",
            "workspace_root": ".",
            "source_ref": "docs/proofs/policy_safety/P1-A/all/20260613T012632Z/manifest.json",
        }
    )
    result = evaluate_research_request(request, evidence=evidence, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "evidence_recorded"
    assert result["research_is_truth"] is False
    assert result["permission_granted"] is False


def test_autonomous_crawl_refused() -> None:
    request = request_from_fixture(
        {
            "request_id": "req-crawl",
            "acquisition_mode": "approved_web_search",
        }
    )
    with pytest.raises(RuntimeContextValidationError) as exc:
        evaluate_research_request(request, observed_at=FIXTURE_CLOCK)
    assert exc.value.code == "res.refused.autonomous_crawl"


def test_unknown_preserved_without_evidence() -> None:
    request = request_from_fixture(
        {
            "request_id": "req-unk",
            "uncertainty": "unknown until supported",
        }
    )
    result = evaluate_research_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "unknown_preserved"
    assert result["research_is_truth"] is False


def test_stale_source_detected() -> None:
    request = request_from_fixture({"request_id": "req-stale", "uncertainty": "bounded"})
    evidence = record_from_provided_file(
        {
            "evidence_id": "ev-stale",
            "expires_at": "2026-06-12T19:00:00.000000Z",
        }
    )
    result = evaluate_research_request(
        request,
        evidence=evidence,
        observed_at="2026-06-12T20:00:00.000000Z",
    )
    assert result["status"] == "stale"
    assert result["reason_code"] == "res.refused.stale_source"


def test_unsupported_claim_without_evidence() -> None:
    request = request_from_fixture({"request_id": "req-none", "uncertainty": "bounded"})
    with pytest.raises(RuntimeContextValidationError):
        evaluate_research_request(request, observed_at=FIXTURE_CLOCK)


def test_research_not_truth_refused() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_research_as_truth(treat_as_truth=True)


def test_record_hash_stable() -> None:
    a = record_from_provided_file({"evidence_id": "stable"})
    b = record_from_provided_file({"evidence_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret_source_ref() -> None:
    with pytest.raises(RuntimeContextValidationError):
        EvidenceRecord(
            evidence_id="bad",
            source_ref="password=secret",
            source_type="uploaded_file",
            claim_supported="x",
            support_level="direct",
            created_at=FIXTURE_CLOCK,
            expires_at="2026-06-13T20:00:00.000000Z",
        )
