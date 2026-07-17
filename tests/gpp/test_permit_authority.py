"""GPP governed permit authority runtime tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.governance.canonical_hash import canonical_hash
from hg_gpp.engine import PermitAuthority, _GPP_ISSUER
from hg_gpp.models import (
    GPP_PERMIT_SCHEMA,
    PermitEvidenceRef,
    PermitRevocation,
    PermitScope,
    PermitVerifier,
    fixture_permit_request,
)
from hg_gpp.validation import (
    DENIED_CAPABILITY_MISMATCH,
    DENIED_MISSING_ADMISSION,
    DENIED_MISSING_EVIDENCE,
    DENIED_MISSING_FRESHNESS,
    DENIED_MISSING_IDENTITY,
    DENIED_MISSING_PROOF,
    DENIED_REDACTION_FAILURE,
    DENIED_RETENTION_FAILURE,
    DENIED_STALE_APPROVAL,
)
from hg_gpp.verifier import verify_permit


def _clock():
    return "2026-06-12T12:00:00.000000Z"


def _authority(**kwargs) -> PermitAuthority:
    return PermitAuthority(clock=_clock, **kwargs)


def test_schema_validation_required_fields():
    request = fixture_permit_request()
    authority = _authority()
    decision = authority.issue(request)

    assert decision.permit is not None
    payload = decision.permit.to_payload()
    for key in (
        "permit_id",
        "request_id",
        "subject_id",
        "agent_id",
        "authority_chain_ref",
        "requested_action_type",
        "scope",
        "evidence_refs",
        "proof_bundle_refs",
        "identity_ref",
        "admission_ref",
        "freshness_ref",
        "redaction_ref",
        "retention_ref",
        "capability_ref",
        "risk_class",
        "issued_at",
        "expires_at",
        "status",
        "permit_hash",
    ):
        assert key in payload
    assert payload["schema"] == GPP_PERMIT_SCHEMA


def test_stable_permit_hash():
    request = fixture_permit_request(request_id="req_hash")
    authority = _authority()
    decision = authority.issue(request)
    permit = decision.permit
    assert permit is not None
    expected = canonical_hash(permit.to_payload(include_hash=False))
    assert permit.permit_hash == expected


def test_permit_grant_positive_fixture():
    authority = _authority()
    decision = authority.issue(fixture_permit_request())

    assert decision.status == "granted"
    assert decision.permit is not None
    assert decision.receipt is not None
    assert decision.receipt.permit_hash == decision.permit.permit_hash
    ok, reason = verify_permit(decision.permit, now=_clock(), store=authority.store)
    assert ok, reason


def test_denial_missing_identity():
    authority = _authority()
    decision = authority.issue(fixture_permit_request(identity_ref="placeholder"))

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_MISSING_IDENTITY in codes


def test_denial_stale_approval():
    authority = _authority()
    decision = authority.issue(
        fixture_permit_request(approval_expires_at="2020-01-01T00:00:00.000000Z")
    )

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_STALE_APPROVAL in codes


def test_denial_missing_admission():
    authority = _authority()
    decision = authority.issue(fixture_permit_request(admission_ref="adm:missing"))

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_MISSING_ADMISSION in codes


def test_denial_missing_freshness():
    authority = _authority()
    decision = authority.issue(fixture_permit_request(freshness_ref="tim:missing"))

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_MISSING_FRESHNESS in codes


def test_denial_missing_proof_refs():
    authority = _authority()
    decision = authority.issue(fixture_permit_request(proof_bundle_refs=()))

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_MISSING_PROOF in codes


def test_denial_missing_evidence():
    authority = _authority()
    decision = authority.issue(fixture_permit_request(evidence_refs=()))

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_MISSING_EVIDENCE in codes


def test_denial_redaction_failure():
    authority = _authority()
    decision = authority.issue(
        fixture_permit_request(
            redaction_ref="sec:redaction_failed",
            redaction_payload={"api_key": "sk-live-secret-token-abcdefghij"},
        )
    )

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_REDACTION_FAILURE in codes


def test_denial_retention_failure():
    authority = _authority()
    decision = authority.issue(fixture_permit_request(retention_ref="ret:missing"))

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_RETENTION_FAILURE in codes


def test_denial_capability_mismatch():
    authority = _authority()
    scope = PermitScope(
        capability_ref="cap.memory_write_stub",
        effect_class="audit_log",
        requested_action_type="oea_stub_log",
    )
    request = fixture_permit_request(
        capability_ref="cap.oea_stub_log",
        scope=scope,
    )
    decision = authority.issue(request)

    assert decision.status == "denied"
    codes = {r.code for r in decision.deny_reasons}
    assert DENIED_CAPABILITY_MISMATCH in codes


def test_permit_expiry():
    authority = PermitAuthority(clock=_clock, permit_ttl_s=1.0)
    decision = authority.issue(fixture_permit_request())
    permit = decision.permit
    assert permit is not None

    ok, reason = verify_permit(
        permit,
        now="2026-06-12T12:05:00.000000Z",
        store=authority.store,
    )
    assert not ok
    assert "expired" in reason


def test_permit_revocation():
    authority = _authority()
    decision = authority.issue(fixture_permit_request())
    permit = decision.permit
    assert permit is not None

    authority.revoke(
        PermitRevocation(
            permit_id=permit.permit_id,
            revoked_at=_clock(),
            reason_code="operator_revoke",
            revoker_ref="op:local",
        )
    )
    ok, reason = verify_permit(permit, now=_clock(), store=authority.store)
    assert not ok
    assert "revoked" in reason


def test_permit_scope_mismatch_on_verify():
    authority = _authority()
    decision = authority.issue(fixture_permit_request())
    permit = decision.permit
    assert permit is not None

    ok, reason = verify_permit(
        permit,
        now=_clock(),
        store=authority.store,
        action_type="external_post",
        capability_ref="cap.external_post",
        effect_class="external_write",
    )
    assert not ok
    assert "scope" in reason


def test_replay_determinism():
    request = fixture_permit_request(request_id="req_replay")
    first = _authority().issue(request)
    second = _authority().issue(request)

    assert first.permit is not None and second.permit is not None
    assert first.permit.permit_hash == second.permit.permit_hash
    assert first.permit.permit_id == second.permit.permit_id


def test_no_oea_ter_calls_in_hg_gpp():
    forbidden = ("hg_oea", "hg_ter", "oea.execute", "ter.execute", "requests.", "httpx.")
    for path in Path("hg_gpp").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"


def test_no_ueak_execution_side_effect():
    authority = _authority()
    authority.issue(fixture_permit_request())
    assert authority.store.execution_log == []


def test_no_hal_soar_self_authorization():
    authority = _authority()
    decision = authority.issue(
        fixture_permit_request(requestor_id=_GPP_ISSUER, authority_chain_ref="dec_hal_accept")
    )
    assert decision.status == "denied"
    assert any("self_mint" in r.code for r in decision.deny_reasons)


def test_proof_bundle_receipt_validation():
    authority = _authority()
    decision = authority.issue(fixture_permit_request())
    receipt = decision.receipt
    assert receipt is not None
    body = {
        "schema": "gpp-permit-receipt",
        "schema_version": "1.0",
        "receipt_id": receipt.receipt_id,
        "permit_id": receipt.permit_id,
        "request_id": receipt.request_id,
        "status": receipt.status,
        "issued_at": receipt.issued_at,
        "permit_hash": receipt.permit_hash,
    }
    assert receipt.receipt_hash == canonical_hash(body)
    assert receipt.permit_hash == decision.permit.permit_hash  # type: ignore[union-attr]


def test_permit_verifier_class():
    authority = _authority()
    decision = authority.issue(fixture_permit_request())
    verifier = PermitVerifier()
    ok, reason = verifier.verify(
        decision.permit,  # type: ignore[arg-type]
        now=_clock(),
        store=authority.store,
    )
    assert ok, reason


def test_publish_permit_kind():
    authority = _authority()
    decision = authority.issue(fixture_permit_request(permit_kind="publish"))
    assert decision.permit is not None
    assert decision.permit.permit_kind == "publish"


def test_evidence_ref_payload():
    ref = PermitEvidenceRef("ev:trace_1", "decision")
    assert ref.to_payload() == {"ref_id": "ev:trace_1", "kind": "decision"}
