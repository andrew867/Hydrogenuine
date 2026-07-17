"""RIB-SPAWN-LIVE evaluator — governed reproduction spawn; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.policy_safety.hashing import canonical_hash
from hg_core.rib_spawn_live.config import rib_spawn_refuse_authority_conversion, rib_spawn_refuse_inherited_authority
from hg_core.rib_spawn_live.errors import (
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_CHILD_IDENTITY_COLLISION,
    REFUSED_INHERITED_AUTHORITY,
    REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    REFUSED_SECRET_LEAK,
    RIB_SPAWN_AUTHORITY_CONVERSION_CONTAINED,
    RIB_SPAWN_FAKE_SINK,
    RIB_SPAWN_FAILED_CLOSED,
    RIB_SPAWN_PLAN_BOUND,
)
from hg_core.rib_spawn_live.no_authority import advisory_only_marker
from hg_runtime.live_reproduction_spawn.adapter import commit_to_fake_sink, plan_to_fake_sink
from hg_runtime.live_reproduction_spawn.fixtures import load_rib_spawn_fixtures
from hg_runtime.live_reproduction_spawn.rollback import rollback_spawn_plan
from hg_runtime.live_reproduction_spawn.tep_emission import emit_fixture_spawn_plan, run_rib_spawn_fixture_emission
from hg_runtime.live_reproduction_spawn.types import (
    FIXTURE_CLOCK,
    ChildIdentityProfile,
    ChildSpawnReceipt,
    request_from_fixture,
)
from hg_runtime.live_reproduction_spawn.validator import validate_spawn_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    "inherited_authority": REFUSED_INHERITED_AUTHORITY,
}


def _receipt_id(request_id: str, child_iam_ref: str) -> str:
    digest = canonical_hash({"request_id": request_id, "child_iam_ref": child_iam_ref})
    return f"rib-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, RIB_SPAWN_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "live_spawn_performed": False,
        "child_inherits_authority": False,
        "emitted_events": ("RIB_SPAWN_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_reproduction_spawn(
    request_data: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
    inherit_parent_permit: bool = False,
) -> dict[str, object]:
    """Process spawn plan path; fake-sink only."""
    clear_registry_cache()
    load_registry()
    try:
        request = request_from_fixture(request_data)
    except Exception as exc:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": getattr(exc, "code", REFUSED_CHILD_IDENTITY_COLLISION),
            "permission_granted": False,
            "live_spawn_performed": False,
            "emitted_events": ("RIB_SPAWN_FAILED_CLOSED",),
        }

    validated = validate_spawn_request(
        request,
        observed_at=observed_at,
        inherit_parent_permit=inherit_parent_permit,
    )
    if validated.get("status") in ("refused", "contained"):
        return {
            **validated,
            "request": request.to_payload(),
            "permission_granted": False,
            "live_spawn_performed": False,
            "emitted_events": ("RIB_SPAWN_REFUSED",),
        }

    identity = ChildIdentityProfile(
        child_iam_ref=request.child_iam_ref,
        parent_iam_ref=request.parent_iam_ref,
    )
    staged = plan_to_fake_sink(identity, observed_at=observed_at)
    tep_wrapped = emit_fixture_spawn_plan(identity.to_payload())

    receipt = ChildSpawnReceipt(
        receipt_id=_receipt_id(request.request_id, request.child_iam_ref),
        request_id=request.request_id,
        child_iam_ref=request.child_iam_ref,
        parent_iam_ref=request.parent_iam_ref,
        status="recorded",
        reason_code=RIB_SPAWN_PLAN_BOUND,
        operator_ref=request.operator_ref,
        evidence_admissible=bool(validated.get("evidence_admissible")),
        rollback_acknowledged=bool(request.rollback_plan_ref),
    )
    committed = commit_to_fake_sink(receipt, observed_at=observed_at)

    rollback_result: dict[str, object] | None = None
    if request.rollback_plan_ref:
        rollback_result = rollback_spawn_plan(receipt, observed_at=observed_at)
        receipt = ChildSpawnReceipt(
            receipt_id=receipt.receipt_id,
            request_id=receipt.request_id,
            child_iam_ref=receipt.child_iam_ref,
            parent_iam_ref=receipt.parent_iam_ref,
            status="recorded",
            reason_code=RIB_SPAWN_FAKE_SINK,
            operator_ref=receipt.operator_ref,
            evidence_admissible=receipt.evidence_admissible,
            rollback_acknowledged=True,
        )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": RIB_SPAWN_FAKE_SINK,
        "request": request.to_payload(),
        "identity": identity.to_payload(),
        "receipt": receipt.to_payload(),
        "staged_sink": staged,
        "committed_sink": committed,
        "tep_wrapped": tep_wrapped,
        "rollback_result": rollback_result,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "live_spawn_performed": False,
        "child_inherits_authority": False,
        "emitted_events": ("RIB_SPAWN_PLAN_RECORDED", "RIB_SPAWN_FAKE_SINK_COMMITTED"),
        "observed_at": observed_at,
    }


def process_rib_spawn_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and rib_spawn_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["spawn_request"])
            except Exception:
                return {
                    **advisory_only_marker(),
                    "status": "refused",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_SECRET_LEAK,
                    "permission_granted": False,
                    "live_spawn_performed": False,
                    "emitted_events": ("RIB_SPAWN_FAILED_CLOSED",),
                }
        if adversarial in _ADVERSARIAL_REASON:
            if adversarial != "secret_leak":
                return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("spawn_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": RIB_SPAWN_FAILED_CLOSED,
            "permission_granted": False,
            "live_spawn_performed": False,
            "emitted_events": ("RIB_SPAWN_FAILED_CLOSED",),
        }

    try:
        request = request_from_fixture(req_data)
    except Exception as exc:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": getattr(exc, "code", REFUSED_CHILD_IDENTITY_COLLISION),
            "permission_granted": False,
            "live_spawn_performed": False,
            "emitted_events": ("RIB_SPAWN_FAILED_CLOSED",),
        }

    if adversarial == "authority_conversion" and request.treat_as_authority:
        return _contain_adversarial(bundle, signal="authority_conversion")

    inherit = bool(req_data.get("inherit_parent_permit", False))
    if inherit and rib_spawn_refuse_inherited_authority():
        return _contain_adversarial(bundle, signal="inherited_authority")

    result = process_reproduction_spawn(req_data, observed_at=observed_at, inherit_parent_permit=inherit)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_rib_spawn_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_rib_spawn_fixtures()
    results = [process_rib_spawn_bundle(b, observed_at=observed_at) for b in bundles]
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rib_spawn.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_live_spawn": all(r.get("live_spawn_performed") is not True for r in results),
        "no_inherited_authority": all(r.get("child_inherits_authority") is not True for r in results),
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
        result = process_rib_spawn_bundle(bundle, observed_at=observed_at)
        results.append(result)
        receipt = result.get("receipt")
        identity = result.get("identity")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
        elif isinstance(identity, dict):
            hashes.append(str(identity.get("record_hash", "")))
        else:
            hashes.append(str(result.get("reason_code", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def run_reproduction_spawn_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    valid_bundle = next(b for b in load_rib_spawn_fixtures() if b["bundle_id"] == "rib-valid-spawn")
    spawn = process_rib_spawn_bundle(valid_bundle, observed_at=observed_at)
    tep = run_rib_spawn_fixture_emission(spawn)
    rollback_bundle = next(b for b in load_rib_spawn_fixtures() if b["bundle_id"] == "rib-valid-rollback")
    rollback_path = process_rib_spawn_bundle(rollback_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rib_spawn.advisory.spawn_adapter_fixture",
        "spawn_result": spawn,
        "rollback_result": rollback_path,
        "tep_emission": tep,
        "live_spawn_performed": False,
        "child_inherits_authority": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = [
    "analyze_rib_spawn_fixtures",
    "process_reproduction_spawn",
    "process_rib_spawn_bundle",
    "replay_fixture_stream",
    "run_reproduction_spawn_fixture",
]
