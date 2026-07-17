"""GMG-LIVE evaluator — governed grant authority; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.gmg_live.config import gmg_refuse_authority_conversion
from hg_core.gmg_live.errors import (
    GMG_AUTHORITY_CONVERSION_CONTAINED,
    GMG_COMMIT_FAKE_SINK,
    GMG_FAILED_CLOSED,
    GMG_REVOCATION_RECORDED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    REFUSED_SECRET_LEAK,
)
from hg_core.gmg_live.no_authority import advisory_only_marker
from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.grant_authority_live.adapter import commit_to_fake_sink, request_to_fake_sink
from hg_runtime.grant_authority_live.fixtures import load_gmg_fixtures
from hg_runtime.grant_authority_live.revocation import record_grant_expiry, revoke_grant
from hg_runtime.grant_authority_live.tep_emission import emit_fixture_grant_candidate, run_gmg_fixture_emission
from hg_runtime.grant_authority_live.types import (
    FIXTURE_CLOCK,
    GrantCandidate,
    GrantReceipt,
    request_from_fixture,
)
from hg_runtime.grant_authority_live.validator import validate_grant_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
}


def _candidate_id(request_id: str, grant_type: str) -> str:
    digest = canonical_hash({"request_id": request_id, "grant_type": grant_type})
    return f"gmg-cand-{digest.rsplit(':', 1)[-1][:12]}"


def _receipt_id(request_id: str, candidate_id: str) -> str:
    digest = canonical_hash({"request_id": request_id, "candidate_id": candidate_id})
    return f"gmg-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, GMG_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "live_grant_performed": False,
        "live_action_performed": False,
        "emitted_events": ("GMG_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_grant_authority(
    request_data: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process request/commit path for grant authority; fake-sink only."""
    clear_registry_cache()
    load_registry()
    request = request_from_fixture(request_data)
    validated = validate_grant_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        return {
            **validated,
            "request": request.to_payload(),
            "permission_granted": False,
            "live_grant_performed": False,
            "live_action_performed": False,
            "emitted_events": ("GMG_GRANT_REFUSED",),
        }

    grant_target = str(request.grant_target() or "")

    if request.control_kind == "revoke":
        candidate = GrantCandidate(
            candidate_id=_candidate_id(request.request_id, request.grant_type),
            request_id=request.request_id,
            grant_type=request.grant_type,
            grant_target=grant_target,
            operator_ref=request.operator_ref,
            gpp_permit_ref=request.gpp_permit_ref,
            rollback_plan_ref=request.rollback_plan_ref,
        )
        staged = request_to_fake_sink(candidate, observed_at=observed_at)
        tep_wrapped = emit_fixture_grant_candidate(candidate.to_payload())
        receipt = GrantReceipt(
            receipt_id=_receipt_id(request.request_id, candidate.candidate_id),
            request_id=request.request_id,
            candidate_id=candidate.candidate_id,
            grant_type=request.grant_type,
            status="recorded",
            reason_code=GMG_REVOCATION_RECORDED,
            operator_ref=request.operator_ref,
            evidence_admissible=bool(validated.get("evidence_admissible")),
            permit_bound=bool(request.gpp_permit_ref),
            revocation_available=True,
        )
        committed = commit_to_fake_sink(receipt, observed_at=observed_at)
        revocation_result = revoke_grant(receipt, grant_target=grant_target, observed_at=observed_at)
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": GMG_REVOCATION_RECORDED,
            "request": request.to_payload(),
            "candidate": candidate.to_payload(),
            "receipt": receipt.to_payload(),
            "staged_sink": staged,
            "committed_sink": committed,
            "tep_wrapped": tep_wrapped,
            "revocation_result": revocation_result,
            "evidence_admissible": validated.get("evidence_admissible", False),
            "permission_granted": False,
            "live_grant_performed": False,
            "live_action_performed": False,
            "emitted_events": ("GMG_REVOCATION_RECORDED",),
            "observed_at": observed_at,
        }

    candidate = GrantCandidate(
        candidate_id=_candidate_id(request.request_id, request.grant_type),
        request_id=request.request_id,
        grant_type=request.grant_type,
        grant_target=grant_target,
        operator_ref=request.operator_ref,
        gpp_permit_ref=request.gpp_permit_ref,
        rollback_plan_ref=request.rollback_plan_ref,
    )
    staged = request_to_fake_sink(candidate, observed_at=observed_at)
    tep_wrapped = emit_fixture_grant_candidate(candidate.to_payload())

    receipt = GrantReceipt(
        receipt_id=_receipt_id(request.request_id, candidate.candidate_id),
        request_id=request.request_id,
        candidate_id=candidate.candidate_id,
        grant_type=request.grant_type,
        status="recorded",
        reason_code=str(validated.get("reason_code", "")),
        operator_ref=request.operator_ref,
        evidence_admissible=bool(validated.get("evidence_admissible")),
        permit_bound=bool(request.gpp_permit_ref),
        revocation_available=bool(request.rollback_plan_ref),
    )
    committed = commit_to_fake_sink(receipt, observed_at=observed_at)

    revocation_result: dict[str, object] | None = None
    expiry_result: dict[str, object] | None = None
    if request.rollback_plan_ref:
        revocation_result = revoke_grant(receipt, grant_target=grant_target, observed_at=observed_at)
        receipt = GrantReceipt(
            receipt_id=receipt.receipt_id,
            request_id=receipt.request_id,
            candidate_id=receipt.candidate_id,
            grant_type=receipt.grant_type,
            status="recorded",
            reason_code=GMG_COMMIT_FAKE_SINK,
            operator_ref=receipt.operator_ref,
            evidence_admissible=receipt.evidence_admissible,
            permit_bound=receipt.permit_bound,
            revocation_available=True,
        )
    if request.grant_expires_at:
        expiry_result = record_grant_expiry(
            receipt,
            grant_target=grant_target,
            grant_expires_at=request.grant_expires_at,
            observed_at=observed_at,
        )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": GMG_COMMIT_FAKE_SINK,
        "request": request.to_payload(),
        "candidate": candidate.to_payload(),
        "receipt": receipt.to_payload(),
        "staged_sink": staged,
        "committed_sink": committed,
        "tep_wrapped": tep_wrapped,
        "revocation_result": revocation_result,
        "expiry_result": expiry_result,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "live_grant_performed": False,
        "live_action_performed": False,
        "emitted_events": ("GMG_GRANT_CANDIDATE_RECORDED", "GMG_FAKE_SINK_COMMITTED"),
        "observed_at": observed_at,
    }


def process_gmg_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and gmg_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["grant_request"])
            except Exception:
                return {
                    **advisory_only_marker(),
                    "status": "refused",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_SECRET_LEAK,
                    "permission_granted": False,
                    "live_grant_performed": False,
                    "live_action_performed": False,
                    "emitted_events": ("GMG_FAILED_CLOSED",),
                }
        if adversarial in _ADVERSARIAL_REASON:
            if adversarial != "secret_leak":
                return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("grant_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": GMG_FAILED_CLOSED,
            "permission_granted": False,
            "live_grant_performed": False,
            "live_action_performed": False,
            "emitted_events": ("GMG_FAILED_CLOSED",),
        }

    try:
        request = request_from_fixture(req_data)
    except Exception as exc:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": getattr(exc, "code", REFUSED_SECRET_LEAK),
            "permission_granted": False,
            "live_grant_performed": False,
            "live_action_performed": False,
            "emitted_events": ("GMG_FAILED_CLOSED",),
        }

    if adversarial == "authority_conversion" and request.treat_as_authority:
        return _contain_adversarial(bundle, signal="authority_conversion")

    result = process_grant_authority(req_data, observed_at=observed_at)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_gmg_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_gmg_fixtures()
    results = [process_gmg_bundle(b, observed_at=observed_at) for b in bundles]
    all_non_authority = all(r.get("permission_granted") is False for r in results)
    no_live_grants = all(r.get("live_grant_performed") is not True for r in results)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "gmg.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all_non_authority,
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_live_grants": no_live_grants,
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
        result = process_gmg_bundle(bundle, observed_at=observed_at)
        results.append(result)
        receipt = result.get("receipt")
        candidate = result.get("candidate")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
        elif isinstance(candidate, dict):
            hashes.append(str(candidate.get("record_hash", "")))
        else:
            hashes.append(str(result.get("reason_code", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def run_grant_authority_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Runtime adapter entry — fixture request/commit with TEP emission."""
    valid_bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-valid-tool-grant")
    grant_result = process_gmg_bundle(valid_bundle, observed_at=observed_at)
    tep = run_gmg_fixture_emission(grant_result)
    revoke_bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-valid-revoke")
    revoke_path = process_gmg_bundle(revoke_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "gmg.advisory.grant_adapter_fixture",
        "grant_result": grant_result,
        "revoke_result": revoke_path,
        "tep_emission": tep,
        "live_grant_performed": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = [
    "analyze_gmg_fixtures",
    "process_gmg_bundle",
    "process_grant_authority",
    "replay_fixture_stream",
    "run_grant_authority_fixture",
]
