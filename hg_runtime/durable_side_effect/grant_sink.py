"""GMG-DSE — governed durable grant registry sink."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import dse_grant_registry_root, ensure_sandbox_dirs
from hg_core.dse.errors import REFUSED_AUTHORITY_EXPANSION
from hg_core.dse.no_authority import advisory_only_marker
from hg_core.dse.policy import SinkClass
from hg_core.dse.sandbox import deterministic_filename
from hg_core.governance.canonical_hash import canonical_hash
from hg_runtime.durable_side_effect.fixtures import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
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

TRANCHE_ID = "GMG-DSE"
DEFAULT_GRANT_TTL_S = 3600


def _registry_path() -> Any:
    return dse_grant_registry_root() / "grants.jsonl"


def process_gmg_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    if bundle.get("permanent_grant"):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_AUTHORITY_EXPANSION, "bundle_id": bundle.get("bundle_id")}

    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(admission_data, tranche_id=TRANCHE_ID, sink_class=SinkClass.DURABLE_SQLITE_OR_STORE_SINK)
    decision = evaluate_sink_admission(request, observed_at=observed_at, expected_sink_class=SinkClass.DURABLE_SQLITE_OR_STORE_SINK)
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    action = bundle.get("action", "create")
    grant_id = bundle.get("grant_id", f"grant-{request.request_id[-8:]}")
    registry = _registry_path()
    registry.parent.mkdir(parents=True, exist_ok=True)

    if action == "revoke":
        entry = {"grant_id": grant_id, "action": "revoke", "observed_at": observed_at}
    elif action == "expire":
        entry = {"grant_id": grant_id, "action": "expire", "expires_at": observed_at, "observed_at": observed_at}
    else:
        entry = {
            "grant_id": grant_id,
            "action": "create",
            "grant_type": bundle.get("grant_type", "tool"),
            "expires_at": bundle.get("expires_at", FUTURE_EXPIRY),
            "ttl_s": bundle.get("ttl_s", DEFAULT_GRANT_TTL_S),
            "permanent": False,
            "observed_at": observed_at,
        }

    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")

    receipt_path = dse_grant_registry_root() / deterministic_filename("grant-rcpt", request.request_id)
    receipt_path.write_text(json.dumps({"grant_id": grant_id, "entry": entry}, indent=2) + "\n", encoding="utf-8")

    result.update(
        {
            **advisory_only_marker(),
            "status": "committed",
            "durable_write_performed": True,
            "sink_class": SinkClass.DURABLE_SQLITE_OR_STORE_SINK.value,
            "grant_receipt": {"grant_id": grant_id, "digest": canonical_hash(entry), "receipt_path": receipt_path.name},
            "rollback": {"grant_id": grant_id, "compensate": "revoke"},
            "observed_at": observed_at,
        }
    )
    return result


def load_gmg_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "gmg-dse-valid-create", "admission": {**VALID_ADMISSION, "request_id": "gmg-dse-create"}, "action": "create"},
        {"bundle_id": "gmg-dse-valid-revoke", "admission": {**VALID_ADMISSION, "request_id": "gmg-dse-revoke"}, "action": "revoke", "grant_id": "grant-test-1"},
        {"bundle_id": "gmg-dse-valid-expire", "admission": {**VALID_ADMISSION, "request_id": "gmg-dse-expire"}, "action": "expire", "grant_id": "grant-test-2"},
        refusal_bundle("gmg-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "gmg-dse-missing-approval"}),
        refusal_bundle("gmg-dse-stale-approval", {**STALE_APPROVAL, "request_id": "gmg-dse-stale-approval"}),
        refusal_bundle("gmg-dse-missing-iam", {**MISSING_IAM, "request_id": "gmg-dse-missing-iam"}),
        refusal_bundle("gmg-dse-missing-tim", {**MISSING_TIM, "request_id": "gmg-dse-missing-tim"}),
        refusal_bundle("gmg-dse-missing-gpp", {**MISSING_GPP, "request_id": "gmg-dse-missing-gpp"}),
        refusal_bundle("gmg-dse-missing-ueak", {**MISSING_UEAK, "request_id": "gmg-dse-missing-ueak"}),
        refusal_bundle("gmg-dse-secret-leak", {**SECRET_LEAK, "request_id": "gmg-dse-secret"}),
        {"bundle_id": "gmg-dse-permanent-refused", "admission": {**VALID_ADMISSION, "request_id": "gmg-dse-perm"}, "permanent_grant": True},
    ]


__all__ = ["TRANCHE_ID", "load_gmg_dse_fixtures", "process_gmg_dse_bundle"]
