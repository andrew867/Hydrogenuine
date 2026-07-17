"""OEA-TER-LIVE evaluator — governed live OEA/TER bridge; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.oea_ter_live.config import oea_ter_refuse_authority_conversion
from hg_core.oea_ter_live.errors import (
    OEA_TER_AUTHORITY_CONVERSION_CONTAINED,
    OEA_TER_COMMIT_FAKE_SINK,
    OEA_TER_COMPENSATION_RECORDED,
    OEA_TER_FAILED_CLOSED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    REFUSED_SECRET_LEAK,
)
from hg_core.oea_ter_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_oea_ter_bridge.adapter import commit_to_fake_sink, request_to_fake_sink
from hg_runtime.live_oea_ter_bridge.fixtures import load_oea_ter_fixtures
from hg_runtime.live_oea_ter_bridge.rollback import compensate_from_rollback, rollback_live_action
from hg_runtime.live_oea_ter_bridge.tep_emission import emit_fixture_dispatch_candidate, run_oea_ter_fixture_emission
from hg_runtime.live_oea_ter_bridge.types import (
    FIXTURE_CLOCK,
    LiveActionCandidate,
    LiveActionReceipt,
    request_from_fixture,
)
from hg_runtime.live_oea_ter_bridge.validator import validate_dispatch_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
}


def _candidate_id(request_id: str, external_surface: str) -> str:
    digest = canonical_hash({"request_id": request_id, "external_surface": external_surface})
    return f"oea-cand-{digest.rsplit(':', 1)[-1][:12]}"


def _receipt_id(request_id: str, candidate_id: str) -> str:
    digest = canonical_hash({"request_id": request_id, "candidate_id": candidate_id})
    return f"oea-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, OEA_TER_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "live_action_performed": False,
        "oea_ter_called": False,
        "emitted_events": ("OEA_TER_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_live_dispatch(
    request_data: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process request/commit path for live dispatch; fake-sink only."""
    clear_registry_cache()
    load_registry()
    request = request_from_fixture(request_data)
    validated = validate_dispatch_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        return {
            **validated,
            "request": request.to_payload(),
            "permission_granted": False,
            "live_action_performed": False,
            "oea_ter_called": False,
            "emitted_events": ("OEA_TER_DISPATCH_REFUSED",),
        }

    if request.control_kind == "compensate":
        rollback_record = {
            "rollback_id": f"oea-rbk-compensate-{request.request_id[-8:]}",
            "action_digest": request.action_digest,
        }
        compensation_result = compensate_from_rollback(
            rollback_record,
            compensation_digest=request.compensation_plan_ref or f"comp:{request.action_digest}",
            observed_at=observed_at,
        )
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": OEA_TER_COMPENSATION_RECORDED,
            "request": request.to_payload(),
            "compensation_result": compensation_result,
            "evidence_admissible": validated.get("evidence_admissible", False),
            "permission_granted": False,
            "live_action_performed": False,
            "oea_ter_called": False,
            "emitted_events": ("OEA_TER_COMPENSATION_RECORDED",),
            "observed_at": observed_at,
        }

    candidate = LiveActionCandidate(
        candidate_id=_candidate_id(request.request_id, request.external_surface),
        request_id=request.request_id,
        external_surface=request.external_surface,
        action_digest=request.action_digest,
        operator_ref=request.operator_ref,
        gpp_permit_ref=request.gpp_permit_ref,
        ueak_admission_ref=request.ueak_admission_ref,
        rollback_plan_ref=request.rollback_plan_ref,
    )
    staged = request_to_fake_sink(candidate, observed_at=observed_at)
    tep_wrapped = emit_fixture_dispatch_candidate(candidate.to_payload())

    receipt = LiveActionReceipt(
        receipt_id=_receipt_id(request.request_id, candidate.candidate_id),
        request_id=request.request_id,
        candidate_id=candidate.candidate_id,
        external_surface=request.external_surface,
        status="recorded",
        reason_code=str(validated.get("reason_code", "")),
        operator_ref=request.operator_ref,
        evidence_admissible=bool(validated.get("evidence_admissible")),
        permit_bound=bool(request.gpp_permit_ref),
        admission_bound=bool(request.ueak_admission_ref),
        rollback_acknowledged=bool(request.rollback_plan_ref),
        compensation_available=bool(request.compensation_plan_ref),
        kill_switch_active=request.kill_switch_active,
    )
    committed = commit_to_fake_sink(receipt, observed_at=observed_at)

    rollback_result: dict[str, object] | None = None
    if request.rollback_plan_ref:
        rollback_result = rollback_live_action(
            receipt,
            action_digest=request.action_digest,
            prior_digest=f"prior:{request.action_digest}",
            observed_at=observed_at,
        )
        receipt = LiveActionReceipt(
            receipt_id=receipt.receipt_id,
            request_id=receipt.request_id,
            candidate_id=receipt.candidate_id,
            external_surface=receipt.external_surface,
            status="recorded",
            reason_code=OEA_TER_COMMIT_FAKE_SINK,
            operator_ref=receipt.operator_ref,
            evidence_admissible=receipt.evidence_admissible,
            permit_bound=receipt.permit_bound,
            admission_bound=receipt.admission_bound,
            rollback_acknowledged=True,
            compensation_available=receipt.compensation_available,
            kill_switch_active=receipt.kill_switch_active,
        )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": OEA_TER_COMMIT_FAKE_SINK,
        "request": request.to_payload(),
        "candidate": candidate.to_payload(),
        "receipt": receipt.to_payload(),
        "staged_sink": staged,
        "committed_sink": committed,
        "tep_wrapped": tep_wrapped,
        "rollback_result": rollback_result,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "live_action_performed": False,
        "oea_ter_called": False,
        "emitted_events": ("OEA_TER_DISPATCH_CANDIDATE_RECORDED", "OEA_TER_FAKE_SINK_COMMITTED"),
        "observed_at": observed_at,
    }


def process_oea_ter_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and oea_ter_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["dispatch_request"])
            except Exception:
                return {
                    **advisory_only_marker(),
                    "status": "refused",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_SECRET_LEAK,
                    "permission_granted": False,
                    "live_action_performed": False,
                    "oea_ter_called": False,
                    "emitted_events": ("OEA_TER_FAILED_CLOSED",),
                }
        if adversarial in _ADVERSARIAL_REASON:
            if adversarial != "secret_leak":
                return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("dispatch_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": OEA_TER_FAILED_CLOSED,
            "permission_granted": False,
            "live_action_performed": False,
            "oea_ter_called": False,
            "emitted_events": ("OEA_TER_FAILED_CLOSED",),
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
            "live_action_performed": False,
            "oea_ter_called": False,
            "emitted_events": ("OEA_TER_FAILED_CLOSED",),
        }

    if adversarial == "authority_conversion" and request.treat_as_authority:
        return _contain_adversarial(bundle, signal="authority_conversion")

    result = process_live_dispatch(req_data, observed_at=observed_at)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_oea_ter_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_oea_ter_fixtures()
    results = [process_oea_ter_bundle(b, observed_at=observed_at) for b in bundles]
    all_non_authority = all(r.get("permission_granted") is False for r in results)
    no_live = all(r.get("live_action_performed") is not True for r in results)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "oea_ter.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all_non_authority,
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_live_actions": no_live,
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
        result = process_oea_ter_bundle(bundle, observed_at=observed_at)
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


def run_oea_ter_bridge_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Runtime adapter entry — fixture request/commit with TEP emission."""
    valid_bundle = next(b for b in load_oea_ter_fixtures() if b["bundle_id"] == "oea-valid-dispatch")
    dispatch_result = process_oea_ter_bundle(valid_bundle, observed_at=observed_at)
    tep = run_oea_ter_fixture_emission(dispatch_result)
    rollback_bundle = next(b for b in load_oea_ter_fixtures() if b["bundle_id"] == "oea-valid-rollback")
    rollback_path = process_oea_ter_bundle(rollback_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "oea_ter.advisory.bridge_adapter_fixture",
        "dispatch_result": dispatch_result,
        "rollback_result": rollback_path,
        "tep_emission": tep,
        "live_action_performed": False,
        "oea_ter_called": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = [
    "analyze_oea_ter_fixtures",
    "process_oea_ter_bundle",
    "process_live_dispatch",
    "replay_fixture_stream",
    "run_oea_ter_bridge_fixture",
]
