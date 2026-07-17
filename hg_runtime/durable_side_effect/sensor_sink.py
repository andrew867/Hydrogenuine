"""SEN-DSE — governed local sensor fixture/device ingestion sink."""

from __future__ import annotations

import json
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import dse_sensor_sink_root, ensure_sandbox_dirs
from hg_core.dse.errors import REFUSED_SILENT_SENSOR
from hg_core.dse.no_authority import advisory_only_marker
from hg_core.dse.policy import SinkClass
from hg_core.dse.sandbox import deterministic_filename
from hg_core.governance.canonical_hash import canonical_hash
from hg_core.secrets.redact import redact_payload
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

TRANCHE_ID = "SEN-DSE"


def _tep_observation(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "tep_schema": "tep_observation_v1",
        "non_authoritative": True,
        "permission_granted": False,
        "payload_digest": canonical_hash(payload),
        "body": payload,
    }


def process_sen_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    if not bundle.get("fixture_enabled") and not bundle.get("device_enabled"):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_SILENT_SENSOR, "bundle_id": bundle.get("bundle_id")}

    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(
        admission_data,
        tranche_id=TRANCHE_ID,
        sink_class=SinkClass.LOCAL_SENSOR_FIXTURE_OR_DEVICE_SINK,
    )
    decision = evaluate_sink_admission(
        request,
        observed_at=observed_at,
        expected_sink_class=SinkClass.LOCAL_SENSOR_FIXTURE_OR_DEVICE_SINK,
    )
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    raw_observation = bundle.get("observation", {"sensor": "fixture", "value": "ambient-ok"})
    observation = redact_payload(raw_observation)

    out_root = dse_sensor_sink_root()
    out_root.mkdir(parents=True, exist_ok=True)
    out_path = out_root / deterministic_filename("sen", request.request_id)
    tep = _tep_observation(observation)
    out_path.write_text(json.dumps({"tep_wrapped": tep, "observation": observation}, indent=2) + "\n", encoding="utf-8")

    result.update(
        {
            **advisory_only_marker(),
            "status": "committed",
            "durable_write_performed": True,
            "sink_class": SinkClass.LOCAL_SENSOR_FIXTURE_OR_DEVICE_SINK.value,
            "tep_wrapped": tep,
            "ingestion_receipt": {"path": out_path.name, "digest": canonical_hash(observation)},
            "observed_at": observed_at,
        }
    )
    return result


def load_sen_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "sen-dse-valid-fixture", "admission": {**VALID_ADMISSION, "request_id": "sen-dse-valid"}, "fixture_enabled": True},
        {"bundle_id": "sen-dse-silent-refused", "admission": {**VALID_ADMISSION, "request_id": "sen-dse-silent"}},
        refusal_bundle("sen-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "sen-dse-missing-approval"}),
        refusal_bundle("sen-dse-stale-approval", {**STALE_APPROVAL, "request_id": "sen-dse-stale-approval"}),
        refusal_bundle("sen-dse-missing-iam", {**MISSING_IAM, "request_id": "sen-dse-missing-iam"}),
        refusal_bundle("sen-dse-missing-tim", {**MISSING_TIM, "request_id": "sen-dse-missing-tim"}),
        refusal_bundle("sen-dse-missing-gpp", {**MISSING_GPP, "request_id": "sen-dse-missing-gpp"}),
        refusal_bundle("sen-dse-missing-ueak", {**MISSING_UEAK, "request_id": "sen-dse-missing-ueak"}),
        refusal_bundle("sen-dse-secret-leak", {**SECRET_LEAK, "request_id": "sen-dse-secret"}),
    ]


__all__ = ["TRANCHE_ID", "load_sen_dse_fixtures", "process_sen_dse_bundle"]
