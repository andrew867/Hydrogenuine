"""End-to-end authority chain integration tests — SOAR → HAL → GPP → UEAK."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from hg_authority_chain import FIXTURE_CLOCK, build_pipeline, run_authority_chain
from hg_authority_chain.pipeline import _proposal_payload
from hg_gpp.validation import DENIED_DECISION_DENIED
from hg_hal.validation import DENIED_PANIC_ACTIVE
from hg_hal import fixture_hal_request
from hg_soar.events import SOAR_HAL_ROUTE_REQUESTED
from hg_soar.validation import DENIED_REDACTION_FAILURE as SOAR_DENIED_REDACTION, DENIED_STALE_APPROVAL as SOAR_DENIED_STALE
from hg_ueak import (
    AuthorityChain,
    DENIED_CAPABILITY_MISMATCH,
    DENIED_EXPIRED_PERMIT,
    DENIED_INVALID_PERMIT,
    DENIED_MISSING_ADMISSION,
    DENIED_MISSING_PERMIT,
    DENIED_PANIC_LOCKDOWN,
    ExecutionAuthorityKernel,
    RollbackRequirement,
    fixture_execution_request,
)


def test_positive_chain_soar_hal_gpp_ueak_fake_dispatch():
    _, _, _, kernel = build_pipeline()
    result = run_authority_chain()
    assert result.completed
    assert result.soar_decision.binding == "ACCEPT"
    assert result.hal_decision.decision_state == "route_to_GPP"
    assert result.permit_decision is not None
    assert result.permit_decision.status == "granted"
    assert result.ueak_decision is not None
    assert result.ueak_decision.status == "admitted"
    assert result.ueak_decision.dispatch_plan is not None
    assert result.ueak_decision.dispatch_plan.sink == "fake_dispatch"
    assert kernel.dispatch_sink.live_execution_log == []
    assert any(e.event_type == SOAR_HAL_ROUTE_REQUESTED for e in result.soar_events)


def test_hal_routes_gpp_without_minting_permit():
    result = run_authority_chain()
    assert result.hal_decision.decision_state == "route_to_GPP"
    payload = result.hal_decision.to_payload()
    assert "permit_id" not in payload
    assert result.permit_decision is not None
    assert result.permit_decision.status == "granted"


def test_gpp_issues_scoped_permit():
    result = run_authority_chain()
    permit = result.permit_decision.permit
    assert permit is not None
    assert permit.capability_ref == "cap.oea_stub_log"
    assert permit.scope.effect_class == "audit_log"


def test_ueak_admits_with_valid_permit():
    result = run_authority_chain()
    assert result.ueak_decision is not None
    assert result.ueak_decision.status == "admitted"
    assert result.ueak_decision.receipt is not None
    assert result.ueak_decision.receipt.receipt_hash


def test_ueak_fake_dispatch_sink_only():
    pipeline = build_pipeline()
    result = run_authority_chain(pipeline=pipeline)
    _, _, _, kernel = pipeline
    assert result.ueak_decision is not None
    assert result.ueak_decision.dispatch_plan.sink == "fake_dispatch"
    assert len(kernel.dispatch_sink.dispatches) == 1
    assert kernel.dispatch_sink.dispatches[0].sink == "fake_dispatch"


def test_deny_missing_permit_at_ueak():
    pipeline = build_pipeline()
    result = run_authority_chain(pipeline=pipeline)
    permit = result.permit_decision.permit
    assert permit is not None
    _, _, _, kernel = pipeline
    refused = kernel.admit(
        replace(
            fixture_execution_request(permit, rollback=RollbackRequirement(required=False)),
            permit=None,
        )
    )
    assert refused.status == "refused"
    assert any(r.code == DENIED_MISSING_PERMIT for r in refused.refusal_reasons)


def test_deny_expired_permit():
    pipeline = build_pipeline()
    result = run_authority_chain(pipeline=pipeline)
    permit = result.permit_decision.permit
    assert permit is not None
    _, _, permit_authority, _ = pipeline
    expired_kernel = ExecutionAuthorityKernel(
        permit_store=permit_authority.store,
        clock=lambda: "2099-01-01T00:00:00.000000Z",
    )
    refused = expired_kernel.admit(
        fixture_execution_request(permit, rollback=RollbackRequirement(required=False))
    )
    assert refused.status == "refused"
    assert any(r.code == DENIED_EXPIRED_PERMIT for r in refused.refusal_reasons)


def test_deny_stale_approval():
    result = run_authority_chain(
        soar_overrides={"approval_expires_at": "2020-01-01T00:00:00.000000Z"},
        gpp_overrides={"approval_expires_at": "2020-01-01T00:00:00.000000Z"},
        ueak_overrides={"approval_expires_at": "2020-01-01T00:00:00.000000Z"},
    )
    assert result.aborted_stage == "SOAR"
    assert any(r.code == SOAR_DENIED_STALE for r in result.soar_decision.reasons)


def test_deny_sec_redaction_failure():
    result = run_authority_chain(
        soar_overrides={"redaction_ref": "sec:redaction_failed"},
        gpp_overrides={"redaction_ref": "sec:redaction_failed"},
        ueak_overrides={"redaction_ref": "sec:redaction_failed"},
    )
    assert result.aborted_stage == "SOAR"
    assert any(r.code == SOAR_DENIED_REDACTION for r in result.soar_decision.reasons)
    result = run_authority_chain(ueak_overrides={"panic_lockdown": True})
    assert result.aborted_stage == "UEAK"
    assert result.ueak_decision is not None
    assert any(r.code == DENIED_PANIC_LOCKDOWN for r in result.ueak_decision.refusal_reasons)


def test_deny_adm_panic_lockdown():
    result = run_authority_chain(
        ueak_overrides={
            "capability_id": "cap.external_post",
            "effect_class": "external_write",
            "action_type": "external_write",
        }
    )
    assert result.aborted_stage == "UEAK"
    assert result.ueak_decision is not None
    assert any(r.code == DENIED_CAPABILITY_MISMATCH for r in result.ueak_decision.refusal_reasons)


def test_soar_reject_blocks_hal_gpp_path():
    result = run_authority_chain(
        soar_overrides={"proposal_payload": _proposal_payload(hard_veto=True)},
    )
    assert result.aborted_stage == "SOAR"
    assert result.soar_decision.binding == "REJECT"
    assert result.permit_decision is None


def test_soar_cannot_bypass_hal():
    result = run_authority_chain(hal_overrides={"soar_binding": "REJECT"})
    assert result.aborted_stage == "HAL"
    assert result.hal_decision.decision_state in {"reject", "request_clarification", "fail_closed"}
    assert result.permit_decision is None


def test_hal_cannot_bypass_gpp():
    result = run_authority_chain(gpp_overrides={"authority_chain_ref": "dec_hal_reject"})
    assert result.aborted_stage == "GPP"
    assert result.permit_decision is not None
    assert result.permit_decision.status == "denied"
    assert any(r.code == DENIED_DECISION_DENIED for r in result.permit_decision.permit.deny_reasons)
    assert result.ueak_decision is None


def test_ueak_cannot_bypass_gpp():
    result = run_authority_chain(gpp_overrides={"authority_chain_ref": "dec_hal_reject"})
    assert result.aborted_stage == "GPP"
    assert result.ueak_decision is None


def test_gpp_cannot_execute():
    _, _, permit_authority, _ = build_pipeline()
    run_authority_chain()
    assert permit_authority._oea_ter_calls == []
    assert not hasattr(permit_authority, "execute")
    assert not hasattr(permit_authority, "dispatch")


def test_hal_panic_blocks_forward_routing():
    _, hal_runtime, _, _ = build_pipeline()
    hal_runtime.enter_panic(reason_code="chain_test")
    hal_decision, _ = hal_runtime.process(fixture_hal_request(request_id="panic_hal"))
    assert hal_decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_PANIC_ACTIVE for r in hal_decision.reasons)


def test_authority_chain_document_complete():
    result = run_authority_chain()
    doc = result.to_authority_chain_document()
    assert doc["schema"] == "authority_chain_proof_v1"
    assert len(doc["stages"]) == 4
    assert doc["refs"]["gpp_permit_id"]
    assert doc["refs"]["gpp_permit_hash"]
    assert doc["chain_hash"]


def test_chain_refs_propagate_through_stages():
    result = run_authority_chain()
    refs = result.refs()
    doc = result.to_authority_chain_document()
    assert refs.proposal_ref == "prop_chain"
    assert refs.soar_run_ref == result.soar_decision.decision_id
    assert refs.hal_decision_ref == result.hal_decision.decision_id
    assert refs.gpp_permit_id == result.permit_decision.permit.permit_id
    assert refs.gpp_permit_hash == result.permit_decision.permit.permit_hash
    assert doc["refs"]["soar_run_ref"] == refs.soar_run_ref
    assert doc["refs"]["hal_decision_ref"] == refs.hal_decision_ref


def test_deny_authority_chain_permit_mismatch_in_chain():
    pipeline = build_pipeline()
    result = run_authority_chain(pipeline=pipeline)
    permit = result.permit_decision.permit
    assert permit is not None
    _, _, _, kernel = pipeline
    refused = kernel.admit(
        replace(
            fixture_execution_request(permit, rollback=RollbackRequirement(required=False)),
            authority_chain=AuthorityChain(
                proposal_ref="prop_chain",
                hal_decision_ref=result.hal_decision.decision_id,
                soar_run_ref=result.soar_decision.decision_id,
                gpp_permit_id="gpp_wrong",
                gpp_permit_hash=permit.permit_hash,
            ),
        )
    )
    assert refused.status == "refused"
    assert any(r.code == DENIED_INVALID_PERMIT for r in refused.refusal_reasons)


def test_replay_deterministic_chain_hash():
    r1 = run_authority_chain()
    r2 = run_authority_chain()
    assert r1.to_authority_chain_document()["chain_hash"] == r2.to_authority_chain_document()["chain_hash"]


def test_no_oea_ter_in_authority_chain_package():
    forbidden = ("hg_oea", "hg_ter", "import requests", "import httpx", "subprocess.")
    for path in Path("hg_authority_chain").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"


def test_deny_missing_admission_in_chain():
    result = run_authority_chain(ueak_overrides={"admission_ref": "adm:missing"})
    assert result.aborted_stage == "UEAK"
    assert result.ueak_decision is not None
    assert any(r.code == DENIED_MISSING_ADMISSION for r in result.ueak_decision.refusal_reasons)
