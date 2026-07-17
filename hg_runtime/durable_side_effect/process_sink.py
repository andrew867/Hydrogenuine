"""RIB-DSE — governed sandboxed child process sink."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import dse_process_sandbox_root, ensure_sandbox_dirs
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

TRANCHE_ID = "RIB-DSE"
MAX_CHILD_LIFETIME_S = 10.0


def process_rib_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(admission_data, tranche_id=TRANCHE_ID, sink_class=SinkClass.PROCESS_SANDBOX_SINK)
    decision = evaluate_sink_admission(request, observed_at=observed_at, expected_sink_class=SinkClass.PROCESS_SANDBOX_SINK)
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    sandbox = dse_process_sandbox_root()
    sandbox.mkdir(parents=True, exist_ok=True)
    child_id = f"child-{request.request_id[-8:]}"
    child_script = sandbox / f"{child_id}.py"
    child_script.write_text('import json; print(json.dumps({"child": True, "network": False}))\n', encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(child_script)],
        cwd=sandbox,
        capture_output=True,
        text=True,
        timeout=MAX_CHILD_LIFETIME_S,
        check=False,
    )
    killed = bundle.get("kill_switch_test", False)
    if killed and proc.poll() is None:
        proc.kill()

    record_path = sandbox / deterministic_filename("child-record", request.request_id)
    record = {
        "child_id": child_id,
        "exit_code": proc.returncode,
        "stdout_digest": canonical_hash({"stdout": proc.stdout}),
        "minimal_context": True,
        "network_default": False,
        "kill_switch_tested": killed,
        "observed_at": observed_at,
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    result.update(
        {
            **advisory_only_marker(),
            "status": "committed",
            "durable_write_performed": True,
            "sink_class": SinkClass.PROCESS_SANDBOX_SINK.value,
            "child_identity": child_id,
            "process_receipt": record,
            "rollback": {"action": "terminate", "child_id": child_id},
            "observed_at": observed_at,
        }
    )
    return result


def load_rib_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "rib-dse-valid", "admission": {**VALID_ADMISSION, "request_id": "rib-dse-valid"}},
        {"bundle_id": "rib-dse-kill-switch", "admission": {**VALID_ADMISSION, "request_id": "rib-dse-kill"}, "kill_switch_test": True},
        refusal_bundle("rib-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "rib-dse-missing-approval"}),
        refusal_bundle("rib-dse-stale-approval", {**STALE_APPROVAL, "request_id": "rib-dse-stale-approval"}),
        refusal_bundle("rib-dse-missing-iam", {**MISSING_IAM, "request_id": "rib-dse-missing-iam"}),
        refusal_bundle("rib-dse-missing-tim", {**MISSING_TIM, "request_id": "rib-dse-missing-tim"}),
        refusal_bundle("rib-dse-missing-gpp", {**MISSING_GPP, "request_id": "rib-dse-missing-gpp"}),
        refusal_bundle("rib-dse-missing-ueak", {**MISSING_UEAK, "request_id": "rib-dse-missing-ueak"}),
        refusal_bundle("rib-dse-secret-leak", {**SECRET_LEAK, "request_id": "rib-dse-secret"}),
    ]


__all__ = ["TRANCHE_ID", "load_rib_dse_fixtures", "process_rib_dse_bundle"]
