"""ALOOP-LIVE evaluator — governed autonomous loop supervisor; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.aloop_live.config import aloop_refuse_authority_conversion, aloop_refuse_self_renewal
from hg_core.aloop_live.errors import (
    ALOOP_FAKE_SINK,
    ALOOP_FAILED_CLOSED,
    ALOOP_LEASE_BOUND,
    ALOOP_PAUSE_RECORDED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    REFUSED_SECRET_LEAK,
    REFUSED_SELF_RENEWAL,
    ALOOP_AUTHORITY_CONVERSION_CONTAINED,
)
from hg_core.aloop_live.no_authority import advisory_only_marker
from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_autonomous_loop.adapter import lease_to_fake_sink, supervise_to_fake_sink
from hg_runtime.live_autonomous_loop.fixtures import load_aloop_fixtures
from hg_runtime.live_autonomous_loop.rollback import record_loop_pause, rollback_loop_supervisor
from hg_runtime.live_autonomous_loop.tep_emission import emit_fixture_loop_lease, run_aloop_fixture_emission
from hg_runtime.live_autonomous_loop.types import (
    FIXTURE_CLOCK,
    AutonomousLoopRequest,
    LoopLease,
    LoopSupervisorReceipt,
    request_from_fixture,
)
from hg_runtime.live_autonomous_loop.validator import validate_loop_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    "self_renewal": REFUSED_SELF_RENEWAL,
}


def _lease_id(request_id: str, loop_scope: str) -> str:
    digest = canonical_hash({"request_id": request_id, "loop_scope": loop_scope})
    return f"aloop-lease-{digest.rsplit(':', 1)[-1][:12]}"


def _receipt_id(request_id: str, lease_id: str) -> str:
    digest = canonical_hash({"request_id": request_id, "lease_id": lease_id})
    return f"aloop-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, ALOOP_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "live_loop_started": False,
        "emitted_events": ("ALOOP_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_autonomous_loop(
    request_data: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process loop supervisor path; fake-sink only."""
    clear_registry_cache()
    load_registry()
    request = request_from_fixture(request_data)
    validated = validate_loop_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        return {
            **validated,
            "request": request.to_payload(),
            "permission_granted": False,
            "live_loop_started": False,
            "emitted_events": ("ALOOP_LOOP_REFUSED",),
        }

    lease = LoopLease(
        lease_id=_lease_id(request.request_id, request.loop_scope),
        request_id=request.request_id,
        loop_scope=request.loop_scope,
        lease_expires_at=request.lease_expires_at,
        heartbeat_ref=request.heartbeat_ref,
        budget_ref=request.budget_ref,
        operator_ref=request.operator_ref,
    )
    staged = lease_to_fake_sink(lease, observed_at=observed_at)
    tep_wrapped = emit_fixture_loop_lease(lease.to_payload())

    supervisor_state = "paused" if request.pause_requested else "supervised"
    reason_code = ALOOP_PAUSE_RECORDED if request.pause_requested else ALOOP_LEASE_BOUND

    receipt = LoopSupervisorReceipt(
        receipt_id=_receipt_id(request.request_id, lease.lease_id),
        request_id=request.request_id,
        lease_id=lease.lease_id,
        supervisor_state=supervisor_state,  # type: ignore[arg-type]
        status="recorded",
        reason_code=reason_code,
        operator_ref=request.operator_ref,
        evidence_admissible=bool(validated.get("evidence_admissible")),
        rollback_acknowledged=bool(request.rollback_plan_ref),
    )
    committed = supervise_to_fake_sink(receipt, observed_at=observed_at)

    rollback_result: dict[str, object] | None = None
    pause_result: dict[str, object] | None = None
    if request.pause_requested:
        pause_result = record_loop_pause(receipt, observed_at=observed_at)
    if request.rollback_plan_ref:
        rollback_result = rollback_loop_supervisor(receipt, observed_at=observed_at)
        receipt = LoopSupervisorReceipt(
            receipt_id=receipt.receipt_id,
            request_id=receipt.request_id,
            lease_id=receipt.lease_id,
            supervisor_state=receipt.supervisor_state,
            status="recorded",
            reason_code=ALOOP_FAKE_SINK,
            operator_ref=receipt.operator_ref,
            evidence_admissible=receipt.evidence_admissible,
            rollback_acknowledged=True,
        )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ALOOP_FAKE_SINK,
        "request": request.to_payload(),
        "lease": lease.to_payload(),
        "receipt": receipt.to_payload(),
        "staged_sink": staged,
        "committed_sink": committed,
        "tep_wrapped": tep_wrapped,
        "rollback_result": rollback_result,
        "pause_result": pause_result,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "live_loop_started": False,
        "loop_self_renewed": False,
        "emitted_events": ("ALOOP_LEASE_RECORDED", "ALOOP_FAKE_SINK_COMMITTED"),
        "observed_at": observed_at,
    }


def process_aloop_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and aloop_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["loop_request"])
            except Exception:
                return {
                    **advisory_only_marker(),
                    "status": "refused",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_SECRET_LEAK,
                    "permission_granted": False,
                    "live_loop_started": False,
                    "emitted_events": ("ALOOP_FAILED_CLOSED",),
                }
        if adversarial in _ADVERSARIAL_REASON:
            if adversarial != "secret_leak":
                return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("loop_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": ALOOP_FAILED_CLOSED,
            "permission_granted": False,
            "live_loop_started": False,
            "emitted_events": ("ALOOP_FAILED_CLOSED",),
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
            "live_loop_started": False,
            "emitted_events": ("ALOOP_FAILED_CLOSED",),
        }

    if adversarial == "authority_conversion" and request.treat_as_authority:
        return _contain_adversarial(bundle, signal="authority_conversion")

    if adversarial == "self_renewal" and request.self_renewal_requested and aloop_refuse_self_renewal():
        return _contain_adversarial(bundle, signal="self_renewal")

    result = process_autonomous_loop(req_data, observed_at=observed_at)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_aloop_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_aloop_fixtures()
    results = [process_aloop_bundle(b, observed_at=observed_at) for b in bundles]
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "aloop.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_live_loop": all(r.get("live_loop_started") is not True for r in results),
        "no_self_renewal": all(r.get("loop_self_renewed") is not True for r in results),
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
        result = process_aloop_bundle(bundle, observed_at=observed_at)
        results.append(result)
        receipt = result.get("receipt")
        lease = result.get("lease")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
        elif isinstance(lease, dict):
            hashes.append(str(lease.get("record_hash", "")))
        else:
            hashes.append(str(result.get("reason_code", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def run_autonomous_loop_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    valid_bundle = next(b for b in load_aloop_fixtures() if b["bundle_id"] == "aloop-valid-supervise")
    supervise = process_aloop_bundle(valid_bundle, observed_at=observed_at)
    tep = run_aloop_fixture_emission(supervise)
    rollback_bundle = next(b for b in load_aloop_fixtures() if b["bundle_id"] == "aloop-valid-rollback")
    rollback_path = process_aloop_bundle(rollback_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "aloop.advisory.loop_adapter_fixture",
        "supervise_result": supervise,
        "rollback_result": rollback_path,
        "tep_emission": tep,
        "live_loop_started": False,
        "loop_self_renewed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = [
    "analyze_aloop_fixtures",
    "process_aloop_bundle",
    "process_autonomous_loop",
    "replay_fixture_stream",
    "run_autonomous_loop_fixture",
]
