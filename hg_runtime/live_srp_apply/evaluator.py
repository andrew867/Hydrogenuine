"""SRP-LIVE evaluator — governed SRP apply; plan/apply separation; fake sink only."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.policy_safety.hashing import canonical_hash
from hg_core.srp_live.config import srp_refuse_authority_conversion, srp_refuse_self_modification
from hg_core.srp_live.decide import srp_apply_decide
from hg_core.srp_live.errors import (
    APPLY_FAKE,
    APPLY_FAKE_OK,
    FAIL_CLOSED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_SECRET_LEAK,
    REFUSED_SELF_MODIFICATION,
    ROUTE_TO_CHANGE_CONTROL,
    SRP_AUTHORITY_CONVERSION_CONTAINED,
    SRP_COMMIT_FAKE_SINK,
)
from hg_core.srp_live.no_authority import advisory_only_marker
from hg_runtime.live_srp_apply.adapter import apply_to_fake_sink, plan_to_operator_visible
from hg_runtime.live_srp_apply.fixtures import load_srp_fixtures
from hg_runtime.live_srp_apply.rollback import rollback_srp_apply
from hg_runtime.live_srp_apply.tep_emission import emit_fixture_apply_plan, run_srp_fixture_emission
from hg_runtime.live_srp_apply.types import (
    FIXTURE_CLOCK,
    SRPApplyAuditRecord,
    SRPApplyReceipt,
    permit_binding_from_fixture,
    request_from_fixture,
)
from hg_runtime.live_srp_apply.validator import validate_srp_apply_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "self_modification": REFUSED_SELF_MODIFICATION,
    "secret_leak": REFUSED_SECRET_LEAK,
}

_idempotency_cache: dict[str, dict[str, object]] = {}


def _receipt_id(repair_id: str, outcome: str) -> str:
    digest = canonical_hash({"repair_id": repair_id, "outcome": outcome})
    return f"srp-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _audit_id(repair_id: str) -> str:
    digest = canonical_hash({"repair_id": repair_id, "kind": "audit"})
    return f"srp-audit-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, SRP_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "live_landing_performed": False,
        "srp_apply_called": False,
        "emitted_events": ("SRP_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_srp_apply(
    request_data: dict[str, Any],
    *,
    permit_binding_data: dict[str, Any] | None = None,
    change_control_state: dict[str, Any] | None = None,
    boundary_liveness_state: dict[str, Any] | None = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process plan → decide → apply path; fake-sink only."""
    clear_registry_cache()
    load_registry()

    idempotency_key = request_data.get("idempotency_key")
    if idempotency_key and idempotency_key in _idempotency_cache:
        cached = _idempotency_cache[idempotency_key]
        return {**cached, "idempotent_replay": True}

    request = request_from_fixture(request_data)
    validated = validate_srp_apply_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        return {
            **validated,
            "request": request.to_payload(),
            "permission_granted": False,
            "live_landing_performed": False,
            "srp_apply_called": False,
            "emitted_events": ("SRP_APPLY_REFUSED",),
        }

    plan_result = plan_to_operator_visible(request, observed_at=observed_at)
    plan_payload = plan_result.get("plan")
    tep_wrapped = emit_fixture_apply_plan(plan_payload) if isinstance(plan_payload, dict) else {}

    permit_binding = permit_binding_from_fixture(permit_binding_data)
    decision = srp_apply_decide(
        request=request.to_payload(),
        permit_binding=permit_binding.to_payload() if permit_binding else None,
        admission_token={"ueak_admission_ref": permit_binding.ueak_admission_ref} if permit_binding else None,
        change_control_state=change_control_state or {},
        boundary_liveness_state=boundary_liveness_state or {},
    )

    decision_value = decision.get("decision")
    if decision_value != APPLY_FAKE:
        outcome = str(decision_value)
        receipt = SRPApplyReceipt(
            receipt_id=_receipt_id(request.repair_id, outcome),
            repair_id=request.repair_id,
            outcome=outcome,
            permit_ref=permit_binding.gpp_permit_ref if permit_binding else None,
            admission_ref=permit_binding.ueak_admission_ref if permit_binding else None,
            approved_digest=request.approved_digest,
            applied_digest="",
            sandbox_proof_ref=request.sandbox_proof_ref,
            operator_ref=request.operator_ref,
            audit_ref=_audit_id(request.repair_id),
        )
        audit = SRPApplyAuditRecord(
            audit_id=_audit_id(request.repair_id),
            repair_id=request.repair_id,
            request_ref=request.repair_id,
            permit_binding_ref=permit_binding.binding_id if permit_binding else None,
            admission_ref=permit_binding.ueak_admission_ref if permit_binding else None,
            plan_ref=str(plan_payload.get("plan_id")) if isinstance(plan_payload, dict) else None,
            receipt_ref=receipt.receipt_id,
            observed_at=observed_at,
        )
        result = {
            **advisory_only_marker(),
            "status": "refused" if outcome.startswith("REJECT") else "routed",
            "reason_code": decision.get("reason_code"),
            "decision": decision,
            "request": request.to_payload(),
            "plan_result": plan_result,
            "tep_wrapped": tep_wrapped,
            "receipt": receipt.to_payload(),
            "audit": audit.to_payload(),
            "phase_completed": "plan",
            "apply_performed": False,
            "permission_granted": False,
            "live_landing_performed": False,
            "srp_apply_called": False,
            "emitted_events": ("SRP_PLAN_RECORDED", "SRP_APPLY_REFUSED"),
            "observed_at": observed_at,
        }
        if idempotency_key:
            _idempotency_cache[idempotency_key] = result
        return result

    receipt = SRPApplyReceipt(
        receipt_id=_receipt_id(request.repair_id, APPLY_FAKE_OK),
        repair_id=request.repair_id,
        outcome=APPLY_FAKE_OK,
        permit_ref=permit_binding.gpp_permit_ref if permit_binding else None,
        admission_ref=permit_binding.ueak_admission_ref if permit_binding else None,
        approved_digest=request.approved_digest,
        applied_digest=request.change_set_digest,
        sandbox_proof_ref=request.sandbox_proof_ref,
        operator_ref=request.operator_ref,
        audit_ref=_audit_id(request.repair_id),
    )
    applied = apply_to_fake_sink(receipt, observed_at=observed_at)

    rollback_result: dict[str, object] | None = None
    if request.rollback_plan_ref:
        rollback_result = rollback_srp_apply(
            receipt,
            target_ref=request.target_ref,
            prior_digest=f"prior:{request.change_set_digest}",
            observed_at=observed_at,
        )
        receipt = SRPApplyReceipt(
            receipt_id=receipt.receipt_id,
            repair_id=receipt.repair_id,
            outcome=APPLY_FAKE_OK,
            permit_ref=receipt.permit_ref,
            admission_ref=receipt.admission_ref,
            approved_digest=receipt.approved_digest,
            applied_digest=receipt.applied_digest,
            sandbox_proof_ref=receipt.sandbox_proof_ref,
            rollback_refs=(str(rollback_result.get("rollback_record", {}).get("rollback_id", "")),),
            operator_ref=receipt.operator_ref,
            audit_ref=receipt.audit_ref,
        )

    audit = SRPApplyAuditRecord(
        audit_id=_audit_id(request.repair_id),
        repair_id=request.repair_id,
        request_ref=request.repair_id,
        permit_binding_ref=permit_binding.binding_id if permit_binding else None,
        admission_ref=permit_binding.ueak_admission_ref if permit_binding else None,
        plan_ref=str(plan_payload.get("plan_id")) if isinstance(plan_payload, dict) else None,
        receipt_ref=receipt.receipt_id,
        observed_at=observed_at,
    )

    result = {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": SRP_COMMIT_FAKE_SINK,
        "decision": decision,
        "request": request.to_payload(),
        "plan_result": plan_result,
        "tep_wrapped": tep_wrapped,
        "receipt": receipt.to_payload(),
        "applied_sink": applied,
        "rollback_result": rollback_result,
        "audit": audit.to_payload(),
        "phase_completed": "apply",
        "apply_performed": True,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "live_landing_performed": False,
        "srp_apply_called": False,
        "emitted_events": ("SRP_PLAN_RECORDED", "SRP_FAKE_SINK_APPLIED"),
        "observed_at": observed_at,
    }
    if idempotency_key:
        _idempotency_cache[idempotency_key] = result
    return result


def process_srp_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and srp_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["apply_request"])
            except Exception:
                return {
                    **advisory_only_marker(),
                    "status": "refused",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_SECRET_LEAK,
                    "permission_granted": False,
                    "live_landing_performed": False,
                    "srp_apply_called": False,
                    "emitted_events": ("SRP_FAILED_CLOSED",),
                }
        if adversarial in _ADVERSARIAL_REASON:
            if adversarial == "self_modification" and srp_refuse_self_modification():
                try:
                    request_from_fixture(bundle["apply_request"])
                except Exception as exc:
                    return {
                        **advisory_only_marker(),
                        "status": "refused",
                        "bundle_id": bundle.get("bundle_id"),
                        "reason_code": getattr(exc, "code", REFUSED_SELF_MODIFICATION),
                        "permission_granted": False,
                        "live_landing_performed": False,
                        "srp_apply_called": False,
                        "emitted_events": ("SRP_SELF_MODIFICATION_REFUSED",),
                    }
            if adversarial == "authority_conversion":
                return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("apply_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": FAIL_CLOSED,
            "permission_granted": False,
            "live_landing_performed": False,
            "srp_apply_called": False,
            "emitted_events": ("SRP_FAILED_CLOSED",),
        }

    try:
        request_from_fixture(req_data)
    except Exception as exc:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": getattr(exc, "code", REFUSED_SECRET_LEAK),
            "permission_granted": False,
            "live_landing_performed": False,
            "srp_apply_called": False,
            "emitted_events": ("SRP_FAILED_CLOSED",),
        }

    result = process_srp_apply(
        req_data,
        permit_binding_data=bundle.get("permit_binding"),
        change_control_state=bundle.get("change_control_state"),
        boundary_liveness_state=bundle.get("boundary_liveness_state"),
        observed_at=observed_at,
    )
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_srp_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_srp_fixtures()
    results = [process_srp_bundle(b, observed_at=observed_at) for b in bundles]
    all_non_authority = all(r.get("permission_granted") is False for r in results)
    no_live = all(r.get("live_landing_performed") is not True for r in results)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "srp.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all_non_authority,
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_live_landing": no_live,
        "observed_at": observed_at,
    }


def replay_fixture_stream(
    bundles: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for bundle in bundles:
        result = process_srp_bundle(bundle, observed_at=observed_at)
        results.append(result)
        receipt = result.get("receipt")
        plan = result.get("plan_result", {}).get("plan") if isinstance(result.get("plan_result"), dict) else None
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
        elif isinstance(plan, dict):
            hashes.append(str(plan.get("record_hash", "")))
        else:
            hashes.append(str(result.get("reason_code", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def run_srp_apply_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Runtime adapter entry — fixture plan/apply with TEP emission."""
    valid_bundle = next(b for b in load_srp_fixtures() if b["bundle_id"] == "srp-valid-apply")
    apply_result = process_srp_bundle(valid_bundle, observed_at=observed_at)
    tep = run_srp_fixture_emission(apply_result)
    rollback_bundle = next(b for b in load_srp_fixtures() if b["bundle_id"] == "srp-valid-rollback")
    rollback_path = process_srp_bundle(rollback_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "srp.advisory.apply_adapter_fixture",
        "apply_result": apply_result,
        "rollback_result": rollback_path,
        "tep_emission": tep,
        "live_landing_performed": False,
        "srp_apply_called": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def reset_idempotency_cache() -> None:
    _idempotency_cache.clear()


__all__ = [
    "analyze_srp_fixtures",
    "process_srp_apply",
    "process_srp_bundle",
    "replay_fixture_stream",
    "reset_idempotency_cache",
    "run_srp_apply_fixture",
]
