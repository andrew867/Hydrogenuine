"""DSE foundation fixtures and evaluator."""

from __future__ import annotations

from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import ensure_sandbox_dirs
from hg_core.dse.policy import SinkClass
from hg_runtime.durable_side_effect.file_sink import write_durable_file

FIXTURE_CLOCK = "2026-06-13T22:00:00.000000Z"
FUTURE_EXPIRY = "2026-06-15T12:00:00.000000Z"
PAST_EXPIRY = "2026-06-13T12:00:00.000000Z"

FOUNDATION_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "dse-valid-file-sink",
        "admission": {
            "request_id": "dse-req-valid-file",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "payload": {"action": "write_test"},
        },
        "relative_name": "foundation-valid.json",
        "content": {"test": "dse-foundation"},
    },
    {
        "bundle_id": "dse-missing-operator-approval",
        "admission": {
            "request_id": "dse-req-missing-approval",
            "operator_ref": None,
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
        },
    },
    {
        "bundle_id": "dse-stale-approval",
        "admission": {
            "request_id": "dse-req-stale-approval",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": PAST_EXPIRY,
            "scope": "approve_change",
        },
    },
    {
        "bundle_id": "dse-missing-iam",
        "admission": {
            "request_id": "dse-req-missing-iam",
            "operator_ref": "bob",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
        },
    },
    {
        "bundle_id": "dse-missing-tim",
        "admission": {
            "request_id": "dse-req-missing-tim",
            "operator_ref": "op:local",
            "freshness_ref": None,
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
        },
    },
    {
        "bundle_id": "dse-unauthorized-path",
        "admission": {
            "request_id": "dse-req-bad-path",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
        },
        "relative_name": "../../../etc/passwd",
    },
    {
        "bundle_id": "dse-secret-leak",
        "admission": {
            "request_id": "dse-req-secret",
            "operator_ref": "op:local",
            "freshness_ref": "tim:approval_window_ok",
            "approval_expires_at": FUTURE_EXPIRY,
            "scope": "approve_change",
            "payload": {"api_key": "sk-abcdefghijklmnopqrstuvwxyz123456"},
        },
    },
)


def load_foundation_fixtures() -> list[dict[str, Any]]:
    return list(FOUNDATION_FIXTURES)


def process_foundation_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    admission_data = bundle.get("admission", {})
    request = AdmissionRequest.from_fixture(
        admission_data,
        tranche_id="DSE-FOUNDATION",
        sink_class=SinkClass.DURABLE_LOCAL_FILE_SINK,
    )
    decision = evaluate_sink_admission(request, observed_at=observed_at)
    result: dict[str, Any] = {
        "bundle_id": bundle.get("bundle_id"),
        "admission": decision.to_payload(),
        "permission_granted": False,
        "authority_created": False,
    }
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    rel_name = bundle.get("relative_name", "foundation-default.json")
    content = bundle.get("content", {"bundle_id": bundle.get("bundle_id")})
    sink_result = write_durable_file(
        request_id=request.request_id,
        tranche_id="DSE-FOUNDATION",
        relative_name=rel_name,
        content=content if isinstance(content, dict) else {"value": content},
        observed_at=observed_at,
    )
    result.update(sink_result)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


__all__ = [
    "FIXTURE_CLOCK",
    "FUTURE_EXPIRY",
    "PAST_EXPIRY",
    "load_foundation_fixtures",
    "process_foundation_bundle",
]
