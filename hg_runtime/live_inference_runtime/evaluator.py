"""INFER-LIVE evaluator — governed local inference runtime; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.infer_live.config import infer_refuse_authority_conversion
from hg_core.infer_live.errors import (
    INFER_AUTHORITY_CONVERSION_CONTAINED,
    INFER_DRY_RUN_COMPLETE,
    INFER_ESCALATION_REQUEST,
    INFER_FAILED_CLOSED,
    INFER_OUTPUT_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_CONTEXT_GRANT_FROM_INFER,
    REFUSED_ESCALATION_AS_AUTHORITY,
    REFUSED_INFERENCE_AS_PERMISSION,
    REFUSED_INSUFFICIENT_HARDWARE,
    REFUSED_LIVE_BACKEND_CALL,
    REFUSED_MEMORY_GRANT_FROM_INFER,
    REFUSED_MODEL_DOWNLOAD,
    REFUSED_TOOL_GRANT_FROM_INFER,
)
from hg_core.infer_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_inference_runtime.adapter import run_dry_run_inference
from hg_runtime.live_inference_runtime.fixtures import load_infer_fixtures
from hg_runtime.live_inference_runtime.hardware import (
    detect_hardware_profile,
    select_backend,
    validate_minimum_hardware,
)
from hg_runtime.live_inference_runtime.model_registry import assign_model_for_organ, cuda_is_optional_only
from hg_runtime.live_inference_runtime.tep_emission import emit_fixture_inference_output, run_infer_fixture_emission
from hg_runtime.live_inference_runtime.types import (
    FIXTURE_CLOCK,
    classify_infer_claim_risk,
    request_from_fixture,
)
from hg_runtime.live_inference_runtime.validator import validate_inference_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "inference_as_permission": REFUSED_INFERENCE_AS_PERMISSION,
    "model_download": REFUSED_MODEL_DOWNLOAD,
    "live_backend_call": REFUSED_LIVE_BACKEND_CALL,
    "tool_grant": REFUSED_TOOL_GRANT_FROM_INFER,
    "memory_grant": REFUSED_MEMORY_GRANT_FROM_INFER,
    "context_grant": REFUSED_CONTEXT_GRANT_FROM_INFER,
    "escalation_as_authority": REFUSED_ESCALATION_AS_AUTHORITY,
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
}


def _contain(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, INFER_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "emitted_events": ("INFER_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_infer_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal") or classify_infer_claim_risk(str(bundle.get("notes", "")))
    if adversarial and infer_refuse_authority_conversion():
        if adversarial in _ADVERSARIAL_REASON and adversarial not in ("model_download", "live_backend_call"):
            return _contain(bundle, signal=str(adversarial))

    hw_fixture = bundle.get("hardware_fixture")
    hardware = detect_hardware_profile(fixture=hw_fixture)
    hw_check = validate_minimum_hardware(hardware)
    if hw_check.get("status") == "fail_closed":
        hw_check["bundle_id"] = bundle.get("bundle_id")
        return hw_check

    req_data = bundle.get("infer_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": INFER_FAILED_CLOSED,
            "permission_granted": False,
        }

    clear_registry_cache()
    load_registry()
    request = request_from_fixture(req_data)
    validated = validate_inference_request(request, observed_at=observed_at)

    if validated.get("status") in ("refused", "contained"):
        validated["bundle_id"] = bundle.get("bundle_id")
        validated["hardware"] = hardware.to_payload()
        return validated

    if request.escalation_requested:
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": INFER_ESCALATION_REQUEST,
            "escalation_is_request_not_authority": True,
            "permission_granted": False,
            "hardware": hardware.to_payload(),
        }

    if adversarial == "live_backend_call" or (not request.dry_run and infer_refuse_authority_conversion()):
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_LIVE_BACKEND_CALL,
            "live_backend_called": False,
            "permission_granted": False,
        }

    dry_run = run_dry_run_inference(request, hardware, observed_at=observed_at)
    tep = emit_fixture_inference_output(dry_run.get("output", {})) if dry_run.get("output") else {}
    backend = dry_run.get("backend_used", select_backend(hardware))

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": INFER_DRY_RUN_COMPLETE if dry_run.get("dry_run") else INFER_OUTPUT_BOUND,
        "validated": validated,
        "dry_run_result": dry_run,
        "tep_wrapped": tep,
        "hardware": hardware.to_payload(),
        "backend_used": backend,
        "cuda_optional_only": cuda_is_optional_only(),
        "nvidia_required": hardware.nvidia_required,
        "live_backend_called": False,
        "permission_granted": False,
        "emitted_events": ("INFER_DRY_RUN_RECORDED",),
        "observed_at": observed_at,
    }


def analyze_infer_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_infer_fixtures()
    results = [process_infer_bundle(b, observed_at=observed_at) for b in bundles]
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_live_backend_calls": all(r.get("live_backend_called") is not True for r in results),
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
        result = process_infer_bundle(bundle, observed_at=observed_at)
        results.append(result)
        out = result.get("dry_run_result", {})
        if isinstance(out, dict):
            output = out.get("output")
            if isinstance(output, dict):
                hashes.append(str(output.get("record_hash", "")))
        hashes.append(str(result.get("reason_code", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def run_inference_runtime_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    hardware = detect_hardware_profile()
    assigned = assign_model_for_organ("organ:OEF", depth="low")
    valid = next(b for b in load_infer_fixtures() if b["bundle_id"] == "infer-valid-dry-run")
    result = process_infer_bundle(valid, observed_at=observed_at)
    tep = run_infer_fixture_emission(result)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "infer.advisory.runtime_fixture",
        "hardware_detected": hardware.to_payload(),
        "organ_model_assignment": assigned.to_payload(),
        "infer_result": result,
        "tep_emission": tep,
        "live_backend_called": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = [
    "analyze_infer_fixtures",
    "process_infer_bundle",
    "replay_fixture_stream",
    "run_inference_runtime_fixture",
]
