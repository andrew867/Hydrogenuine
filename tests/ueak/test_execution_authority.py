"""UEAK execution authority kernel runtime tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from hg_core.governance.canonical_hash import canonical_hash
from hg_gpp import PermitAuthority
from hg_gpp.models import PermitRevocation, PermitScope, fixture_permit_request
from hg_ueak import (
    DENIED_CAPABILITY_MISMATCH,
    DENIED_EMERGENCY_RESTRICT,
    DENIED_EXPOSURE_INCREASE,
    DENIED_EXPIRED_PERMIT,
    DENIED_FRESHNESS,
    DENIED_INVALID_PERMIT,
    DENIED_MISSING_ADMISSION,
    DENIED_MISSING_IDENTITY,
    DENIED_MISSING_PERMIT,
    DENIED_MISSING_ROLLBACK,
    DENIED_PANIC_LOCKDOWN,
    DENIED_REDACTION_FAILURE,
    DENIED_RESOURCE_BYPASS,
    DENIED_RETENTION_FAILURE,
    DENIED_REVOKED_PERMIT,
    DENIED_STALE_APPROVAL,
    AuthorityChain,
    EmergencyState,
    ExecutionAuthorityKernel,
    ExecutionRiskEnvelope,
    ExposureSurface,
    ResourceGovernanceEnvelope,
    RollbackRequirement,
    fixture_execution_request,
)


def _clock() -> str:
    return "2026-06-12T15:00:00.000000Z"


def _permit_authority() -> PermitAuthority:
    return PermitAuthority(clock=_clock, permit_ttl_s=300.0)


def _granted_permit():
    authority = _permit_authority()
    decision = authority.issue(fixture_permit_request(request_id="gpp_for_ueak"))
    assert decision.permit is not None
    return authority, decision.permit


def _kernel_with_permit():
    authority, permit = _granted_permit()
    kernel = ExecutionAuthorityKernel(permit_store=authority.store, clock=_clock)
    return kernel, permit


def test_valid_admission_with_valid_permit_fixture():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        rollback=RollbackRequirement(required=False),
    )
    decision = kernel.admit(request)

    assert decision.status == "admitted"
    assert decision.dispatch_plan is not None
    assert decision.receipt is not None
    assert decision.receipt.receipt_hash
    assert len(kernel.dispatch_sink.dispatches) == 1


def test_deny_missing_permit():
    kernel = ExecutionAuthorityKernel(clock=_clock)
    _, permit = _granted_permit()
    request = replace(
        fixture_execution_request(permit, rollback=RollbackRequirement(required=False)),
        permit=None,
    )
    decision = kernel.admit(request)

    assert decision.status == "refused"
    assert any(r.code == DENIED_MISSING_PERMIT for r in decision.refusal_reasons)
    assert decision.receipt is not None
    assert decision.receipt.status == "refused"


def test_deny_expired_permit():
    authority = _permit_authority()
    decision = authority.issue(fixture_permit_request(request_id="exp_permit"))
    permit = decision.permit
    assert permit is not None
    kernel = ExecutionAuthorityKernel(permit_store=authority.store, clock=lambda: "2099-01-01T00:00:00.000000Z")
    request = fixture_execution_request(
        permit,
        rollback=RollbackRequirement(required=False),
    )
    result = kernel.admit(request)
    assert result.status == "refused"
    assert any(r.code == DENIED_EXPIRED_PERMIT for r in result.refusal_reasons)


def test_deny_revoked_permit():
    authority = _permit_authority()
    decision = authority.issue(fixture_permit_request(request_id="rev_permit"))
    permit = decision.permit
    assert permit is not None
    authority.revoke(
        PermitRevocation(
            permit_id=permit.permit_id,
            revoked_at=_clock(),
            reason_code="test_revoke",
            revoker_ref="op:local",
        )
    )
    kernel = ExecutionAuthorityKernel(permit_store=authority.store, clock=_clock)
    request = fixture_execution_request(permit, rollback=RollbackRequirement(required=False))
    result = kernel.admit(request)
    assert result.status == "refused"
    assert any(r.code == DENIED_REVOKED_PERMIT for r in result.refusal_reasons)


def test_deny_missing_freshness():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        freshness_ref="tim:missing",
        rollback=RollbackRequirement(required=False),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_FRESHNESS for r in decision.refusal_reasons)


def test_deny_missing_admission():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        admission_ref="adm:missing",
        rollback=RollbackRequirement(required=False),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_MISSING_ADMISSION for r in decision.refusal_reasons)


def test_deny_missing_retention():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        retention_ref="ret:missing",
        rollback=RollbackRequirement(required=False),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_RETENTION_FAILURE for r in decision.refusal_reasons)


def test_deny_authority_chain_permit_mismatch():
    kernel, permit = _kernel_with_permit()
    request = replace(
        fixture_execution_request(permit, rollback=RollbackRequirement(required=False)),
        authority_chain=AuthorityChain(
            proposal_ref="prop_fixture",
            hal_decision_ref="hal_dec_fixture",
            gpp_permit_id="gpp_wrong",
            gpp_permit_hash=permit.permit_hash,
        ),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_INVALID_PERMIT for r in decision.refusal_reasons)


def test_resource_pressure_bypass_denied():
    kernel = ExecutionAuthorityKernel(clock=_clock)
    _, permit = _granted_permit()
    request = replace(
        fixture_execution_request(
            permit,
            rollback=RollbackRequirement(required=False),
            risk=ExecutionRiskEnvelope(
                resource=ResourceGovernanceEnvelope(pressure_high=True, quota_available=False),
            ),
        ),
        permit=None,
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_RESOURCE_BYPASS for r in decision.refusal_reasons)
    assert any(r.code == DENIED_MISSING_PERMIT for r in decision.refusal_reasons)


def test_deny_stale_approval():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        approval_expires_at="2020-01-01T00:00:00.000000Z",
        rollback=RollbackRequirement(required=False),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_STALE_APPROVAL for r in decision.refusal_reasons)


def test_deny_missing_identity():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        identity_ref="placeholder",
        rollback=RollbackRequirement(required=False),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_MISSING_IDENTITY for r in decision.refusal_reasons)


def test_deny_panic_lockdown():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        panic_lockdown=True,
        rollback=RollbackRequirement(required=False),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_PANIC_LOCKDOWN for r in decision.refusal_reasons)


def test_deny_redaction_failure():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        redaction_ref="sec:redaction_failed",
        rollback=RollbackRequirement(required=False),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_REDACTION_FAILURE for r in decision.refusal_reasons)


def test_deny_capability_mismatch():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(
        permit,
        capability_id="cap.external_post",
        effect_class="external_write",
        rollback=RollbackRequirement(required=True, rollback_ref="rbk:1"),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_CAPABILITY_MISMATCH for r in decision.refusal_reasons)


def test_deny_missing_rollback_requirement():
    authority = _permit_authority()
    pd = authority.issue(
        fixture_permit_request(
            request_id="ext_permit",
            capability_ref="cap.external_write_scaffold",
            scope=PermitScope(
                capability_ref="cap.external_write_scaffold",
                effect_class="external_write",
                requested_action_type="external_write_scaffold",
            ),
        )
    )
    permit = pd.permit
    assert permit is not None
    kernel = ExecutionAuthorityKernel(permit_store=authority.store, clock=_clock)
    request = fixture_execution_request(
        permit,
        capability_id="cap.external_write_scaffold",
        effect_class="external_write",
        action_type="external_write_scaffold",
        rollback=RollbackRequirement(required=True, rollback_ref=""),
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_MISSING_ROLLBACK for r in decision.refusal_reasons)


def test_emergency_restrict_only():
    kernel, permit = _kernel_with_permit()
    risk = ExecutionRiskEnvelope(
        emergency=EmergencyState(active=True, mode="restrict", restrict_only=True),
    )
    request = fixture_execution_request(
        permit,
        capability_id="cap.external_write_scaffold",
        effect_class="external_write",
        rollback=RollbackRequirement(required=True, rollback_ref="rbk:1"),
        risk=risk,
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_EMERGENCY_RESTRICT for r in decision.refusal_reasons)


def test_exposure_surface_detected():
    kernel, permit = _kernel_with_permit()
    risk = ExecutionRiskEnvelope(
        exposure=ExposureSurface(current_level="internal", requested_level="external", increase_explicit=False),
    )
    request = fixture_execution_request(
        permit,
        rollback=RollbackRequirement(required=False),
        risk=risk,
    )
    decision = kernel.admit(request)
    assert decision.status == "refused"
    assert any(r.code == DENIED_EXPOSURE_INCREASE for r in decision.refusal_reasons)


def test_resource_pressure_cannot_bypass():
    kernel, permit = _kernel_with_permit()
    risk = ExecutionRiskEnvelope(
        resource=ResourceGovernanceEnvelope(pressure_high=True, quota_available=True),
    )
    request = fixture_execution_request(
        permit,
        rollback=RollbackRequirement(required=False),
        risk=risk,
    )
    decision = kernel.admit(request)
    assert decision.status == "admitted"


def test_fake_dispatch_only():
    kernel, permit = _kernel_with_permit()
    request = fixture_execution_request(permit, rollback=RollbackRequirement(required=False))
    kernel.admit(request)
    assert len(kernel.dispatch_sink.dispatches) == 1
    assert kernel.dispatch_sink.dispatches[0].sink == "fake_dispatch"
    assert kernel.dispatch_sink.live_execution_log == []


def test_receipt_hashing():
    kernel, permit = _kernel_with_permit()
    decision = kernel.admit(fixture_execution_request(permit, rollback=RollbackRequirement(required=False)))
    receipt = decision.receipt
    assert receipt is not None
    expected = canonical_hash(receipt.to_payload(include_hash=False))
    assert receipt.receipt_hash == expected


def test_replay_determinism():
    kernel1, permit = _kernel_with_permit()
    kernel2, _ = _kernel_with_permit()
    req = fixture_execution_request(permit, request_id="ueak_det", rollback=RollbackRequirement(required=False))
    d1 = kernel1.admit(req)
    d2 = kernel2.admit(req)
    assert d1.decision_hash == d2.decision_hash


def test_no_direct_oea_ter_in_hg_ueak():
    forbidden = ("hg_oea", "hg_ter", "import requests", "import httpx", "subprocess.", "mint_permit")
    runtime_modules = ("kernel.py", "validation.py", "dispatch.py", "models.py")
    for name in runtime_modules:
        path = Path("hg_ueak") / name
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"


def test_no_permit_minting():
    authority = _permit_authority()
    decision = authority.issue(fixture_permit_request(request_id="mint_check"))
    permit = decision.permit
    assert permit is not None
    before = len(authority.store._permits)
    kernel = ExecutionAuthorityKernel(permit_store=authority.store, clock=_clock)
    kernel.admit(fixture_execution_request(permit, rollback=RollbackRequirement(required=False)))
    assert len(authority.store._permits) == before
    assert not hasattr(kernel, "issue")
