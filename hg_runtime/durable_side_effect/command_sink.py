"""OEA-TER-DSE — governed local command sandbox sink."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import dse_command_sandbox_root, ensure_sandbox_dirs
from hg_core.dse.errors import REFUSED_ARBITRARY_SHELL
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

TRANCHE_ID = "OEA-TER-DSE"
ALLOWLISTED_COMMANDS = frozenset({"echo", "python", "dir", "ls"})


def process_oea_ter_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    cmd = bundle.get("command", ["echo", "dse-sandbox-ok"])
    if not cmd or cmd[0] not in ALLOWLISTED_COMMANDS:
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_ARBITRARY_SHELL, "bundle_id": bundle.get("bundle_id")}

    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(admission_data, tranche_id=TRANCHE_ID, sink_class=SinkClass.LOCAL_COMMAND_SANDBOX_SINK)
    decision = evaluate_sink_admission(request, observed_at=observed_at, expected_sink_class=SinkClass.LOCAL_COMMAND_SANDBOX_SINK)
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    timeout_s = float(bundle.get("timeout_s", 5.0))
    cwd = dse_command_sandbox_root()
    cwd.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_s, check=False)

    log_path = cwd / deterministic_filename("cmd-log", request.request_id)
    log_entry = {
        "argv": cmd,
        "exit_code": proc.returncode,
        "stdout_digest": canonical_hash({"stdout": proc.stdout}),
        "stderr_digest": canonical_hash({"stderr": proc.stderr}),
        "observed_at": observed_at,
    }
    log_path.write_text(json.dumps(log_entry, indent=2) + "\n", encoding="utf-8")

    result.update(
        {
            **advisory_only_marker(),
            "status": "committed",
            "durable_write_performed": True,
            "sink_class": SinkClass.LOCAL_COMMAND_SANDBOX_SINK.value,
            "command_receipt": log_entry,
            "command_log_ref": log_path.name,
            "rollback": {"action": "delete_log", "path": log_path.name},
            "observed_at": observed_at,
        }
    )
    return result


def load_oea_ter_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "oea-dse-valid", "admission": {**VALID_ADMISSION, "request_id": "oea-dse-valid"}, "command": ["echo", "dse-ok"]},
        refusal_bundle("oea-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "oea-dse-missing-approval"}),
        refusal_bundle("oea-dse-stale-approval", {**STALE_APPROVAL, "request_id": "oea-dse-stale-approval"}),
        refusal_bundle("oea-dse-missing-iam", {**MISSING_IAM, "request_id": "oea-dse-missing-iam"}),
        refusal_bundle("oea-dse-missing-tim", {**MISSING_TIM, "request_id": "oea-dse-missing-tim"}),
        refusal_bundle("oea-dse-missing-gpp", {**MISSING_GPP, "request_id": "oea-dse-missing-gpp"}),
        refusal_bundle("oea-dse-missing-ueak", {**MISSING_UEAK, "request_id": "oea-dse-missing-ueak"}),
        refusal_bundle("oea-dse-secret-leak", {**SECRET_LEAK, "request_id": "oea-dse-secret"}),
        {"bundle_id": "oea-dse-arbitrary-shell", "admission": {**VALID_ADMISSION, "request_id": "oea-dse-shell"}, "command": ["rm", "-rf", "/"]},
    ]


__all__ = ["TRANCHE_ID", "load_oea_ter_dse_fixtures", "process_oea_ter_dse_bundle"]
