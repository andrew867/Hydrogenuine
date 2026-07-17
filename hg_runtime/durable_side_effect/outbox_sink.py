"""PUB-EXT-DSE — governed local publication outbox sink."""

from __future__ import annotations

import json
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import dse_outbox_root, ensure_sandbox_dirs
from hg_core.dse.errors import REFUSED_PUBLIC_PUBLISH
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

TRANCHE_ID = "PUB-EXT-DSE"


def process_pub_ext_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    if bundle.get("public_api_call"):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_PUBLIC_PUBLISH, "bundle_id": bundle.get("bundle_id")}

    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(admission_data, tranche_id=TRANCHE_ID, sink_class=SinkClass.LOCAL_PUBLICATION_OUTBOX_SINK)
    decision = evaluate_sink_admission(request, observed_at=observed_at, expected_sink_class=SinkClass.LOCAL_PUBLICATION_OUTBOX_SINK)
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    action = bundle.get("action", "stage")
    candidate_id = bundle.get("candidate_id", f"pub-{request.request_id[-8:]}")
    out_root = dse_outbox_root()
    out_root.mkdir(parents=True, exist_ok=True)
    out_path = out_root / deterministic_filename("outbox", candidate_id)

    if action == "withdraw":
        entry = {"candidate_id": candidate_id, "state": "withdrawn", "observed_at": observed_at}
    elif action == "revoke":
        entry = {"candidate_id": candidate_id, "state": "revoked", "observed_at": observed_at}
    else:
        entry = {
            "candidate_id": candidate_id,
            "state": "staged",
            "release_candidate": bundle.get("release_candidate", {"title": "dse-test-release"}),
            "public_internet": False,
            "observed_at": observed_at,
        }

    out_path.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result.update(
        {
            **advisory_only_marker(),
            "status": "committed",
            "durable_write_performed": True,
            "sink_class": SinkClass.LOCAL_PUBLICATION_OUTBOX_SINK.value,
            "outbox_receipt": {"path": out_path.name, "state": entry["state"], "digest": canonical_hash(entry)},
            "rollback": {"action": "withdraw", "candidate_id": candidate_id},
            "observed_at": observed_at,
        }
    )
    return result


def load_pub_ext_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "pub-dse-valid-stage", "admission": {**VALID_ADMISSION, "request_id": "pub-dse-stage"}, "action": "stage"},
        {"bundle_id": "pub-dse-valid-withdraw", "admission": {**VALID_ADMISSION, "request_id": "pub-dse-withdraw"}, "action": "withdraw", "candidate_id": "pub-cand-1"},
        refusal_bundle("pub-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "pub-dse-missing-approval"}),
        refusal_bundle("pub-dse-stale-approval", {**STALE_APPROVAL, "request_id": "pub-dse-stale-approval"}),
        refusal_bundle("pub-dse-missing-iam", {**MISSING_IAM, "request_id": "pub-dse-missing-iam"}),
        refusal_bundle("pub-dse-missing-tim", {**MISSING_TIM, "request_id": "pub-dse-missing-tim"}),
        refusal_bundle("pub-dse-missing-gpp", {**MISSING_GPP, "request_id": "pub-dse-missing-gpp"}),
        refusal_bundle("pub-dse-missing-ueak", {**MISSING_UEAK, "request_id": "pub-dse-missing-ueak"}),
        refusal_bundle("pub-dse-secret-leak", {**SECRET_LEAK, "request_id": "pub-dse-secret"}),
        {"bundle_id": "pub-dse-public-api-refused", "admission": {**VALID_ADMISSION, "request_id": "pub-dse-api"}, "public_api_call": True},
    ]


__all__ = ["TRANCHE_ID", "load_pub_ext_dse_fixtures", "process_pub_ext_dse_bundle"]
