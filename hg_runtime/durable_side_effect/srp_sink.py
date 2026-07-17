"""SRP-DSE — governed restrict-only apply durable sink."""

from __future__ import annotations

import json
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import ensure_sandbox_dirs
from hg_core.dse.errors import REFUSED_AUTHORITY_EXPANSION
from hg_core.dse.no_authority import advisory_only_marker
from hg_core.dse.policy import SinkClass
from hg_runtime.durable_side_effect.file_sink import write_durable_file
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

TRANCHE_ID = "SRP-DSE"


def process_srp_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    if bundle.get("authority_expansion"):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_AUTHORITY_EXPANSION, "bundle_id": bundle.get("bundle_id")}

    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(admission_data, tranche_id=TRANCHE_ID, sink_class=SinkClass.DURABLE_LOCAL_FILE_SINK)
    decision = evaluate_sink_admission(request, observed_at=observed_at, expected_sink_class=SinkClass.DURABLE_LOCAL_FILE_SINK)
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    phase = bundle.get("phase", "plan")
    if phase == "plan":
        result.update({**advisory_only_marker(), "status": "recorded", "phase": "plan", "apply_deferred": True, "durable_write_performed": False})
        return result

    config = {
        "restrict_only": True,
        "authority_expansion": False,
        "repair_id": bundle.get("repair_id", request.request_id),
        "panic_lockout": bundle.get("panic_lockout", False),
    }
    snapshot = {"pre_apply": config, "rollback_snapshot": True}
    sink = write_durable_file(
        request_id=request.request_id,
        tranche_id=TRANCHE_ID,
        relative_name=f"srp-apply-{request.request_id[-8:]}.json",
        content={"config": config, "snapshot": snapshot},
        observed_at=observed_at,
    )
    result.update(sink)
    result["phase"] = "apply"
    result["restrict_only"] = True
    return result


def load_srp_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "srp-dse-valid-plan", "admission": {**VALID_ADMISSION, "request_id": "srp-dse-plan"}, "phase": "plan"},
        {"bundle_id": "srp-dse-valid-apply", "admission": {**VALID_ADMISSION, "request_id": "srp-dse-apply"}, "phase": "apply"},
        refusal_bundle("srp-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "srp-dse-missing-approval"}),
        refusal_bundle("srp-dse-stale-approval", {**STALE_APPROVAL, "request_id": "srp-dse-stale-approval"}),
        refusal_bundle("srp-dse-missing-iam", {**MISSING_IAM, "request_id": "srp-dse-missing-iam"}),
        refusal_bundle("srp-dse-missing-tim", {**MISSING_TIM, "request_id": "srp-dse-missing-tim"}),
        refusal_bundle("srp-dse-missing-gpp", {**MISSING_GPP, "request_id": "srp-dse-missing-gpp"}),
        refusal_bundle("srp-dse-missing-ueak", {**MISSING_UEAK, "request_id": "srp-dse-missing-ueak"}),
        refusal_bundle("srp-dse-secret-leak", {**SECRET_LEAK, "request_id": "srp-dse-secret"}),
        {"bundle_id": "srp-dse-authority-expansion", "admission": {**VALID_ADMISSION, "request_id": "srp-dse-expand"}, "authority_expansion": True},
    ]


__all__ = ["TRANCHE_ID", "load_srp_dse_fixtures", "process_srp_dse_bundle"]
