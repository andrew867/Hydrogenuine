"""INFER-DSE — governed local inference durable sink."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import dse_inference_sink_root, dse_model_cache_root, ensure_sandbox_dirs
from hg_core.dse.errors import REFUSED_MODEL_DOWNLOAD
from hg_core.dse.no_authority import advisory_only_marker
from hg_core.dse.policy import SinkClass
from hg_core.dse.sandbox import deterministic_filename
from hg_core.governance.canonical_hash import canonical_hash
from hg_runtime.durable_side_effect.fixtures import (
    FIXTURE_CLOCK,
    MISSING_APPROVAL,
    MISSING_GPP,
    MISSING_IAM,
    MISSING_TIM,
    MISSING_UEAK,
    SECRET_LEAK,
    STALE_APPROVAL,
    VALID_ADMISSION,
    refusal_bundle,
)
from hg_runtime.live_inference_runtime.hardware import detect_hardware_profile, select_backend, validate_minimum_hardware

TRANCHE_ID = "INFER-DSE"
TINY_MODEL_MARKER = "tiny-approved-local"


def _tep_wrap(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "tep_schema": "tep_observation_v1",
        "non_authoritative": True,
        "permission_granted": False,
        "payload_digest": canonical_hash(payload),
        "body": payload,
    }


def _hardware_receipt() -> dict[str, Any]:
    hw = detect_hardware_profile()
    backend = select_backend(hw)
    check = validate_minimum_hardware(hw)
    return {
        "hardware": hw.to_payload(),
        "backend": backend,
        "readiness": check,
        "openvino_igpu_ready": backend == "openvino_igpu" or hw.igpu_available,
        "cpu_fallback_ready": True,
    }


def _local_model_exists() -> bool:
    marker = dse_model_cache_root() / f"{TINY_MODEL_MARKER}.json"
    return marker.exists()


def process_infer_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    admission_data["request_id"] = bundle.get("admission", {}).get("request_id", admission_data["request_id"])
    request = AdmissionRequest.from_fixture(
        admission_data,
        tranche_id=TRANCHE_ID,
        sink_class=SinkClass.LOCAL_INFERENCE_SINK,
    )
    if bundle.get("model_download_requested"):
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_MODEL_DOWNLOAD,
            "bundle_id": bundle.get("bundle_id"),
        }

    decision = evaluate_sink_admission(
        request,
        observed_at=observed_at,
        expected_sink_class=SinkClass.LOCAL_INFERENCE_SINK,
    )
    result: dict[str, Any] = {
        "bundle_id": bundle.get("bundle_id"),
        "admission": decision.to_payload(),
        "hardware_receipt": _hardware_receipt(),
        "permission_granted": False,
    }
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    output_root = dse_inference_sink_root()
    output_root.mkdir(parents=True, exist_ok=True)
    inference_output = {
        "request_id": request.request_id,
        "model_profile": bundle.get("model_profile", TINY_MODEL_MARKER),
        "dry_run": not _local_model_exists(),
        "output_text": bundle.get("output_text", "fixture-inference-output"),
        "backend": result["hardware_receipt"]["backend"],
    }
    if _local_model_exists() and bundle.get("operator_approved_invoke"):
        inference_output["invoked"] = True
    else:
        inference_output["invoked"] = False
        inference_output["reason"] = "no_local_model_or_operator_fixture"

    out_path = output_root / deterministic_filename("infer", request.request_id)
    out_path.write_text(json.dumps(inference_output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tep = _tep_wrap(inference_output)

    result.update(
        {
            **advisory_only_marker(),
            "status": "committed",
            "durable_write_performed": True,
            "sink_class": SinkClass.LOCAL_INFERENCE_SINK.value,
            "tep_wrapped": tep,
            "inference_receipt": {
                "target_ref": str(out_path.name),
                "content_digest": canonical_hash(inference_output),
                "receipt_hash": canonical_hash({"request_id": request.request_id, "tep": tep}),
            },
            "observed_at": observed_at,
        }
    )
    return result


def load_infer_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {
            "bundle_id": "infer-dse-valid",
            "admission": {**VALID_ADMISSION, "request_id": "infer-dse-valid"},
            "operator_approved_invoke": True,
        },
        refusal_bundle("infer-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "infer-dse-missing-approval"}),
        refusal_bundle("infer-dse-stale-approval", {**STALE_APPROVAL, "request_id": "infer-dse-stale-approval"}),
        refusal_bundle("infer-dse-missing-iam", {**MISSING_IAM, "request_id": "infer-dse-missing-iam"}),
        refusal_bundle("infer-dse-missing-tim", {**MISSING_TIM, "request_id": "infer-dse-missing-tim"}),
        refusal_bundle("infer-dse-missing-gpp", {**MISSING_GPP, "request_id": "infer-dse-missing-gpp"}),
        refusal_bundle("infer-dse-missing-ueak", {**MISSING_UEAK, "request_id": "infer-dse-missing-ueak"}),
        refusal_bundle("infer-dse-secret-leak", {**SECRET_LEAK, "request_id": "infer-dse-secret"}),
        {"bundle_id": "infer-dse-model-download", "model_download_requested": True},
    ]


__all__ = ["TRANCHE_ID", "load_infer_dse_fixtures", "process_infer_dse_bundle"]
