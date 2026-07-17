"""ALOOP-DSE — governed bounded loop supervisor sink."""

from __future__ import annotations

import json
from typing import Any

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.config import dse_loop_supervisor_root, ensure_sandbox_dirs
from hg_core.dse.errors import REFUSED_UNBOUNDED_LOOP
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

TRANCHE_ID = "ALOOP-DSE"
DEFAULT_BUDGET_TICKS = 5
DEFAULT_MAX_RUNTIME_S = 30.0


def process_aloop_dse_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    ensure_sandbox_dirs()
    if bundle.get("unbounded"):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_UNBOUNDED_LOOP, "bundle_id": bundle.get("bundle_id")}

    admission_data = {**VALID_ADMISSION, **bundle.get("admission", {})}
    request = AdmissionRequest.from_fixture(admission_data, tranche_id=TRANCHE_ID, sink_class=SinkClass.LOOP_SUPERVISOR_SINK)
    decision = evaluate_sink_admission(request, observed_at=observed_at, expected_sink_class=SinkClass.LOOP_SUPERVISOR_SINK)
    result: dict[str, Any] = {"bundle_id": bundle.get("bundle_id"), "admission": decision.to_payload(), "permission_granted": False}
    if not decision.admitted:
        result["status"] = "refused"
        result["durable_write_performed"] = False
        return result

    action = bundle.get("action", "run")
    loop_id = bundle.get("loop_id", f"loop-{request.request_id[-8:]}")
    root = dse_loop_supervisor_root()
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / deterministic_filename("loop", loop_id)

    if action == "panic":
        state = {"loop_id": loop_id, "state": "panic", "observed_at": observed_at}
    elif action == "stop":
        state = {"loop_id": loop_id, "state": "stopped", "observed_at": observed_at}
    else:
        budget = int(bundle.get("budget_ticks", DEFAULT_BUDGET_TICKS))
        heartbeats = [{"tick": i, "observed_at": observed_at} for i in range(min(budget, DEFAULT_BUDGET_TICKS))]
        state = {
            "loop_id": loop_id,
            "state": "completed",
            "budget_ticks": budget,
            "max_runtime_s": DEFAULT_MAX_RUNTIME_S,
            "heartbeats": heartbeats,
            "hidden_restart": False,
            "observed_at": observed_at,
        }

    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result.update(
        {
            **advisory_only_marker(),
            "status": "committed",
            "durable_write_performed": True,
            "sink_class": SinkClass.LOOP_SUPERVISOR_SINK.value,
            "loop_receipt": {"loop_id": loop_id, "state": state.get("state"), "digest": canonical_hash(state)},
            "rollback": {"action": "stop", "loop_id": loop_id},
            "observed_at": observed_at,
        }
    )
    return result


def load_aloop_dse_fixtures() -> list[dict[str, Any]]:
    return [
        {"bundle_id": "aloop-dse-valid", "admission": {**VALID_ADMISSION, "request_id": "aloop-dse-valid"}},
        {"bundle_id": "aloop-dse-panic", "admission": {**VALID_ADMISSION, "request_id": "aloop-dse-panic"}, "action": "panic"},
        {"bundle_id": "aloop-dse-unbounded-refused", "admission": {**VALID_ADMISSION, "request_id": "aloop-dse-unbounded"}, "unbounded": True},
        refusal_bundle("aloop-dse-missing-approval", {**MISSING_APPROVAL, "request_id": "aloop-dse-missing-approval"}),
        refusal_bundle("aloop-dse-stale-approval", {**STALE_APPROVAL, "request_id": "aloop-dse-stale-approval"}),
        refusal_bundle("aloop-dse-missing-iam", {**MISSING_IAM, "request_id": "aloop-dse-missing-iam"}),
        refusal_bundle("aloop-dse-missing-tim", {**MISSING_TIM, "request_id": "aloop-dse-missing-tim"}),
        refusal_bundle("aloop-dse-missing-gpp", {**MISSING_GPP, "request_id": "aloop-dse-missing-gpp"}),
        refusal_bundle("aloop-dse-missing-ueak", {**MISSING_UEAK, "request_id": "aloop-dse-missing-ueak"}),
        refusal_bundle("aloop-dse-secret-leak", {**SECRET_LEAK, "request_id": "aloop-dse-secret"}),
    ]


__all__ = ["TRANCHE_ID", "load_aloop_dse_fixtures", "process_aloop_dse_bundle"]
