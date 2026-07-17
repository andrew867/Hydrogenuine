"""CRT export and fake-green prevention tests."""

from __future__ import annotations

import pytest

from hg_core.policy_safety.errors import PolicyValidationError
from hg_runtime.certification_evidence_pack.export import (
    FIXTURE_CLOCK,
    build_auditor_export,
    build_snapshot_from_fixtures,
    export_advisory_payload,
)
from hg_runtime.certification_evidence_pack.types import make_claim

HEAD = "4a2bf6c2075c262f9436586c384f47b5b1b2977e"
EVIDENCE_REF = "ev-p1a-proof"
EVIDENCE_HASH = "sha256:047526882c13a00c984eac013102b5ce2d9634192bdac1f0986c9c5092260ca1"


def _sample_snapshot():
    return build_snapshot_from_fixtures(
        snapshot_id="snap-1",
        branch="main",
        head=HEAD,
        claims=[
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
        exceptions=[
            {
                "exception_id": "exc-rtc",
                "detail": "RTC policy_safety events deferred to post-P1",
                "control_domain": "logging",
            }
        ],
        evidence_refs=[
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
    )


def test_snapshot_branch_head_hashes() -> None:
    snapshot = _sample_snapshot()
    assert snapshot.branch == "main"
    assert snapshot.head == HEAD
    assert snapshot.record_hash.startswith("sha256:") or len(snapshot.record_hash) == 64


def test_unsupported_claim_marked() -> None:
    snapshot = _sample_snapshot()
    unsupported = [c for c in snapshot.claims if c.status == "unsupported"]
    assert len(unsupported) == 1


def test_exception_preserved() -> None:
    snapshot = _sample_snapshot()
    bundle = build_auditor_export(snapshot)
    payload = export_advisory_payload(bundle)
    assert len(payload["snapshot"]["exceptions"]) == 1


def test_stale_evidence_marked_stale() -> None:
    snapshot = _sample_snapshot()
    stale = [r for r in snapshot.evidence_refs if not r.fresh]
    assert len(stale) == 1


def test_fake_green_prevented() -> None:
    with pytest.raises(PolicyValidationError):
        make_claim(
            claim_id="fake",
            statement="everything is production ready",
            control_domain="testing",
            status="supported",
            evidence_refs=(),
            created_at=FIXTURE_CLOCK,
        )


def test_export_reproducible() -> None:
    snapshot = _sample_snapshot()
    a = build_auditor_export(snapshot)
    b = build_auditor_export(snapshot)
    assert a.bundle_hash == b.bundle_hash


def test_export_not_permission() -> None:
    bundle = build_auditor_export(_sample_snapshot())
    payload = export_advisory_payload(bundle)
    assert payload["permission_granted"] is False
    assert payload["certification_granted"] is False


def test_schema_validation_rejects_bad_evidence_hash() -> None:
    with pytest.raises(PolicyValidationError):
        build_snapshot_from_fixtures(
            snapshot_id="snap-bad",
            branch="main",
            head=HEAD,
            claims=[],
            exceptions=[],
            evidence_refs=[
                {
                    "evidence_id": "ev-bad",
                    "path": "docs/proofs/x",
                    "content_hash": "not-a-hash",
                    "fresh": "true",
                }
            ],
        )
