"""OUX-LIVE evaluator — governed operator review console; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.oux_live.config import oux_refuse_authority_conversion
from hg_core.oux_live.errors import (
    OUX_APPROVAL_EVIDENCE_BOUND,
    OUX_AUTHORITY_CONVERSION_CONTAINED,
    OUX_DENIAL_RECORDED,
    OUX_FAILED_CLOSED,
    OUX_PAUSE_RECORDED,
    OUX_PANIC_RESTRICT_RECORDED,
    OUX_RECORDED,
    OUX_REVOCATION_RECORDED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    REFUSED_PANIC_AS_PERMISSION,
    REFUSED_SECRET_LEAK,
)
from hg_core.oux_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_operator_ux.adapter import dispatch_to_fake_sink
from hg_runtime.live_operator_ux.audit import record_audit_event
from hg_runtime.live_operator_ux.fixtures import load_oux_fixtures
from hg_runtime.live_operator_ux.tep_emission import emit_fixture_ux_receipt, run_oux_fixture_emission
from hg_runtime.live_operator_ux.types import (
    FIXTURE_CLOCK,
    OperatorActionRequest,
    OperatorReviewQueueView,
    OperatorUXReceipt,
    action_request_from_fixture,
)
from hg_runtime.live_operator_ux.validator import validate_operator_action_request
from hg_runtime.operator_review_intake import load_static_fixture_requests, process_review_queue

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "panic_as_permission": REFUSED_PANIC_AS_PERMISSION,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
}

_CONTROL_REASON: dict[str, str] = {
    "approve": OUX_APPROVAL_EVIDENCE_BOUND,
    "deny": OUX_DENIAL_RECORDED,
    "revoke": OUX_REVOCATION_RECORDED,
    "pause": OUX_PAUSE_RECORDED,
    "panic": OUX_PANIC_RESTRICT_RECORDED,
}


def _receipt_id(request_id: str, control_kind: str) -> str:
    digest = canonical_hash({"request_id": request_id, "control_kind": control_kind})
    return f"oux-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, OUX_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "emitted_events": ("OUX_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_operator_control(
    request: OperatorActionRequest,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process explicit operator control; receipt remains non-authority."""
    clear_registry_cache()
    load_registry()
    validated = validate_operator_action_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        audit = record_audit_event(
            action_ref=request.request_id,
            operator_ref=request.operator_ref,
            event_code=str(validated.get("reason_code", OUX_FAILED_CLOSED)),
            observed_at=observed_at,
        )
        return {
            **validated,
            "audit_record": audit.to_payload(),
            "permission_granted": False,
            "emitted_events": ("OUX_CONTROL_REFUSED",),
        }

    reason_code = _CONTROL_REASON.get(request.control_kind, OUX_RECORDED)
    receipt = OperatorUXReceipt(
        receipt_id=_receipt_id(request.request_id, request.control_kind),
        request_id=request.request_id,
        control_kind=request.control_kind,
        status="recorded",
        reason_code=reason_code,
        operator_ref=request.operator_ref,
        evidence_admissible=bool(validated.get("evidence_admissible")),
        rollback_acknowledged=request.control_kind in ("revoke", "panic"),
        kill_switch_active=request.control_kind == "panic",
    )
    audit = record_audit_event(
        action_ref=request.request_id,
        operator_ref=request.operator_ref,
        event_code=reason_code,
        observed_at=observed_at,
    )
    sink = dispatch_to_fake_sink(receipt, observed_at=observed_at)
    tep_wrapped = emit_fixture_ux_receipt(receipt.to_payload())
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": reason_code,
        "request": request.to_payload(),
        "receipt": receipt.to_payload(),
        "audit_record": audit.to_payload(),
        "fake_sink": sink,
        "tep_wrapped": tep_wrapped,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": ("OUX_OPERATOR_CONTROL_RECORDED", "OUX_AUDIT_RECORDED"),
        "observed_at": observed_at,
    }


def process_oux_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and oux_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                action_request_from_fixture(bundle["action_request"])
            except Exception:
                return {
                    **advisory_only_marker(),
                    "status": "refused",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_SECRET_LEAK,
                    "permission_granted": False,
                    "emitted_events": ("OUX_FAILED_CLOSED",),
                }
        if adversarial in _ADVERSARIAL_REASON:
            contained = _contain_adversarial(bundle, signal=str(adversarial))
            if adversarial != "secret_leak":
                return contained

    req_data = bundle.get("action_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": OUX_FAILED_CLOSED,
            "permission_granted": False,
            "emitted_events": ("OUX_FAILED_CLOSED",),
        }

    try:
        request = action_request_from_fixture(req_data)
    except Exception as exc:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": getattr(exc, "code", REFUSED_SECRET_LEAK),
            "permission_granted": False,
            "emitted_events": ("OUX_FAILED_CLOSED",),
        }

    result = process_operator_control(request, observed_at=observed_at)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def render_review_queue_view(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Operator-visible queue view from ORI fixtures — digest only, not approval."""
    requests = load_static_fixture_requests()
    queue = process_review_queue(requests, observed_at=observed_at)
    items = queue.get("items", [])
    item_count = len(items) if isinstance(items, list) else 0
    view = OperatorReviewQueueView(
        view_id="oux-queue-view:fixture",
        item_count=item_count,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "oux.advisory.queue_view_rendered",
        "queue_view": view.to_payload(),
        "digest_is_not_approval": True,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def analyze_oux_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_oux_fixtures()
    results = [process_oux_bundle(b, observed_at=observed_at) for b in bundles]
    all_non_authority = all(r.get("permission_granted") is False for r in results)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "oux.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all_non_authority,
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
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
        result = process_oux_bundle(bundle, observed_at=observed_at)
        results.append(result)
        receipt = result.get("receipt")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
        else:
            hashes.append(str(result.get("reason_code", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def run_console_adapter_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Runtime adapter entry — fixture console with ORI queue + TEP emission."""
    queue_view = render_review_queue_view(observed_at=observed_at)
    valid_bundle = next(b for b in load_oux_fixtures() if b["bundle_id"] == "oux-valid-approve")
    control = process_oux_bundle(valid_bundle, observed_at=observed_at)
    tep = run_oux_fixture_emission(control)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "oux.advisory.console_adapter_fixture",
        "queue_view": queue_view,
        "control_result": control,
        "tep_emission": tep,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = [
    "analyze_oux_fixtures",
    "process_operator_control",
    "process_oux_bundle",
    "render_review_queue_view",
    "replay_fixture_stream",
    "run_console_adapter_fixture",
]
