"""REB-DSE — governed sandbox checkpoint restore sink."""

from __future__ import annotations

import json
import shutil
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import dse_checkpoint_root, ensure_sandbox_dirs
from hg_core.dse.errors import REFUSED_IDENTITY_EQUIVALENCE, REFUSED_STALE_CHECKPOINT
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

TRANCHE_ID = "REB-DSE"


def _ensure_checkpoint(checkpoint_id: str, *, stale: bool = False) -> None:
    root = dse_checkpoint_root()
    root.mkdir(parents=True, exist_ok=True)
    cp_dir = root / checkpoint_id
    cp_dir.mkdir(parents=True, exist_ok=True)
    meta = {"checkpoint_id": checkpoint_id, "stale": stale, "content": "fixture-checkpoint"}
    (cp_dir / "checkpoint.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def process_reb_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    checkpoint_id = bundle.get("checkpoint_id", "cp-fresh-001")
    if bundle.get("identity_equivalence"):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_IDENTITY_EQUIVALENCE, "bundle_id": bundle.get("bundle_id")}

    _ensure_checkpoint(checkpoint_id, stale=bool(bundle.get("stale_checkpoint")))
    cp_meta_path = dse_checkpoint_root() / checkpoint_id / "checkpoint.json"
    meta = json.loads(cp_meta_path.read_text(encoding="utf-8"))
    if meta.get("stale"):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_STALE_CHECKPOINT, "bundle_id": bundle.get("bundle_id")}

    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(admission_data, tranche_id=TRANCHE_ID, sink_class=SinkClass.DURABLE_LOCAL_FILE_SINK)
    decision = evaluate_sink_admission(request, observed_at=observed_at, expected_sink_class=SinkClass.DURABLE_LOCAL_FILE_SINK)
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    restore_ns = dse_checkpoint_root() / "restored"
    restore_ns.mkdir(parents=True, exist_ok=True)
    target = restore_ns / deterministic_filename("restore", request.request_id)
    shutil.copytree(dse_checkpoint_root() / checkpoint_id, target, dirs_exist_ok=True)

    result.update(
        {
            **advisory_only_marker(),
            "status": "committed",
            "durable_write_performed": True,
            "sink_class": SinkClass.DURABLE_LOCAL_FILE_SINK.value,
            "restore_receipt": {
                "checkpoint_id": checkpoint_id,
                "restore_path": str(target.relative_to(dse_checkpoint_root())),
                "digest": canonical_hash(meta),
                "continuity_check": "ok",
            },
            "rollback": {"action": "delete_restore", "path": str(target.name)},
            "observed_at": observed_at,
        }
    )
    return result


def load_reb_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "reb-dse-valid", "admission": {**VALID_ADMISSION, "request_id": "reb-dse-valid"}, "checkpoint_id": "cp-fresh-001"},
        {"bundle_id": "reb-dse-stale-checkpoint", "admission": {**VALID_ADMISSION, "request_id": "reb-dse-stale"}, "checkpoint_id": "cp-stale-001", "stale_checkpoint": True},
        {"bundle_id": "reb-dse-identity-guard", "admission": {**VALID_ADMISSION, "request_id": "reb-dse-identity"}, "identity_equivalence": True},
        refusal_bundle("reb-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "reb-dse-missing-approval"}),
        refusal_bundle("reb-dse-stale-approval", {**STALE_APPROVAL, "request_id": "reb-dse-stale-approval"}),
        refusal_bundle("reb-dse-missing-iam", {**MISSING_IAM, "request_id": "reb-dse-missing-iam"}),
        refusal_bundle("reb-dse-missing-tim", {**MISSING_TIM, "request_id": "reb-dse-missing-tim"}),
        refusal_bundle("reb-dse-missing-gpp", {**MISSING_GPP, "request_id": "reb-dse-missing-gpp"}),
        refusal_bundle("reb-dse-missing-ueak", {**MISSING_UEAK, "request_id": "reb-dse-missing-ueak"}),
        refusal_bundle("reb-dse-secret-leak", {**SECRET_LEAK, "request_id": "reb-dse-secret"}),
    ]


__all__ = ["TRANCHE_ID", "load_reb_dse_fixtures", "process_reb_dse_bundle"]
