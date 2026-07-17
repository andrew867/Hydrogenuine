"""MEM-DSE — governed durable memory store sink."""

from __future__ import annotations

from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import ensure_sandbox_dirs
from hg_core.dse.policy import SinkClass
from hg_core.dse.no_authority import advisory_only_marker
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
from hg_runtime.durable_side_effect.store_sink import append_store_record, readback_store

TRANCHE_ID = "MEM-DSE"
NAMESPACE = "mem-live-local"


def process_mem_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(
        admission_data,
        tranche_id=TRANCHE_ID,
        sink_class=SinkClass.DURABLE_SQLITE_OR_STORE_SINK,
    )
    decision = evaluate_sink_admission(request, observed_at=observed_at, expected_sink_class=SinkClass.DURABLE_SQLITE_OR_STORE_SINK)
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    record = {
        "memory_key": bundle.get("memory_key", "mem:session:dse-test"),
        "payload_digest": bundle.get("payload_digest", "digest:mem-dse"),
        "mutation_kind": bundle.get("mutation_kind", "write"),
    }
    sink = append_store_record(
        request_id=request.request_id,
        tranche_id=TRANCHE_ID,
        namespace=NAMESPACE,
        record=record,
        observed_at=observed_at,
    )
    readback = readback_store(NAMESPACE, limit=5)
    result.update(sink)
    result["readback_proof"] = {"count": len(readback), "latest": readback[-1] if readback else None}
    return result


def load_mem_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "mem-dse-valid", "admission": {**VALID_ADMISSION, "request_id": "mem-dse-valid"}},
        refusal_bundle("mem-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "mem-dse-missing-approval"}),
        refusal_bundle("mem-dse-stale-approval", {**STALE_APPROVAL, "request_id": "mem-dse-stale-approval"}),
        refusal_bundle("mem-dse-missing-iam", {**MISSING_IAM, "request_id": "mem-dse-missing-iam"}),
        refusal_bundle("mem-dse-missing-tim", {**MISSING_TIM, "request_id": "mem-dse-missing-tim"}),
        refusal_bundle("mem-dse-missing-gpp", {**MISSING_GPP, "request_id": "mem-dse-missing-gpp"}),
        refusal_bundle("mem-dse-missing-ueak", {**MISSING_UEAK, "request_id": "mem-dse-missing-ueak"}),
        refusal_bundle("mem-dse-secret-leak", {**SECRET_LEAK, "request_id": "mem-dse-secret"}),
    ]


__all__ = ["TRANCHE_ID", "load_mem_dse_fixtures", "process_mem_dse_bundle"]
