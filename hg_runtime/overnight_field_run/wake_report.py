"""Wake report — operator summary after field run."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.overnight_field_run.schema import FieldRunMode, OvernightFieldRunVerdict, field_run_dir, load_field_run_policy, new_id, now_iso


@dataclass
class WakeReport:
    wake_report_id: str
    field_run_id: str
    started_at: str
    stopped_at: str
    elapsed_seconds: float
    turn_count: int
    task_selection_count: int
    governed_work_count: int
    internal_work_count: int
    external_candidate_count: int
    dry_dispatch_count: int
    live_dispatch_count: int
    refusal_count: int
    idle_count: int
    panic_count: int
    stop_reason: str
    top_selected_task_types: list[str] = field(default_factory=list)
    notable_refusals: list[str] = field(default_factory=list)
    incidents: list[str] = field(default_factory=list)
    proof_refs: list[str] = field(default_factory=list)
    receipt_hashes: list[str] = field(default_factory=list)
    operator_summary: str = ""
    verdict: str = ""
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "wake_report_id": self.wake_report_id,
            "field_run_id": self.field_run_id,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "elapsed_seconds": self.elapsed_seconds,
            "turn_count": self.turn_count,
            "task_selection_count": self.task_selection_count,
            "governed_work_count": self.governed_work_count,
            "internal_work_count": self.internal_work_count,
            "external_candidate_count": self.external_candidate_count,
            "dry_dispatch_count": self.dry_dispatch_count,
            "live_dispatch_count": self.live_dispatch_count,
            "refusal_count": self.refusal_count,
            "idle_count": self.idle_count,
            "panic_count": self.panic_count,
            "stop_reason": self.stop_reason,
            "top_selected_task_types": self.top_selected_task_types,
            "notable_refusals": self.notable_refusals,
            "incidents": self.incidents,
            "proof_refs": self.proof_refs,
            "receipt_hashes": self.receipt_hashes,
            "operator_summary": self.operator_summary,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> WakeReport:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return WakeReport(**{**self.__dict__, "hash": compute_record_hash(body)})


def write_wake_report(report: WakeReport, *, base: Path | None = None) -> Path:
    root = field_run_dir(report.field_run_id, base=base)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "wake_report.json"
    path.write_text(json.dumps(report.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_wake_report(field_run_id: str, *, base: Path | None = None) -> WakeReport | None:
    path = field_run_dir(field_run_id, base=base) / "wake_report.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return WakeReport(**data)


def build_wake_report(
    field_run_id: str,
    *,
    mode: str,
    started_at: str,
    stopped_at: str,
    elapsed_seconds: float,
    state_payload: dict[str, Any],
    stop_reason: str,
    task_types: list[str],
    refusals: list[str],
    incidents: list[str],
    receipt_hashes: list[str],
    continuity_verdict: str,
    postflight_verdict: str,
    base: Path | None = None,
) -> WakeReport:
    turn_count = int(state_payload.get("turn_count", 0))
    policy = load_field_run_policy()
    min_elapsed = float(policy.get("min_elapsed_seconds_for_overnight_complete", 3600))
    import os

    fast_turns = os.environ.get("HG_HANDS_OFF_FAST_TURNS") == "1"

    if mode == FieldRunMode.INFRASTRUCTURE_SMOKE.value:
        verdict = OvernightFieldRunVerdict.YELLOW_FIELD_RUN_SHORT_SMOKE_ONLY.value
    elif (
        mode == FieldRunMode.OPERATOR_FIELD_RUN.value
        and turn_count >= 10
        and elapsed_seconds >= min_elapsed
        and not fast_turns
    ):
        verdict = OvernightFieldRunVerdict.GREEN_FIELD_RUN_COMPLETE.value
    elif mode == FieldRunMode.OPERATOR_FIELD_RUN.value:
        verdict = OvernightFieldRunVerdict.YELLOW_OPERATOR_STOPPED.value
    else:
        verdict = OvernightFieldRunVerdict.GREEN_INFRASTRUCTURE_READY.value

    if continuity_verdict.startswith("RED_") or postflight_verdict.startswith("RED_"):
        verdict = postflight_verdict if postflight_verdict.startswith("RED_") else continuity_verdict

    summary_parts = [
        f"Field run {field_run_id} completed with {turn_count} turns.",
        f"Selected tasks: {state_payload.get('task_selection_count', 0)}.",
        f"Governed work items: {state_payload.get('governed_work_count', 0)}.",
        f"External side effects: {state_payload.get('external_side_effect_count', 0)}.",
        f"Stop reason: {stop_reason}.",
    ]
    if refusals:
        summary_parts.append(f"Notable refusals: {', '.join(refusals[:5])}.")

    report = WakeReport(
        wake_report_id=new_id("wake"),
        field_run_id=field_run_id,
        started_at=started_at,
        stopped_at=stopped_at,
        elapsed_seconds=elapsed_seconds,
        turn_count=turn_count,
        task_selection_count=int(state_payload.get("task_selection_count", 0)),
        governed_work_count=int(state_payload.get("governed_work_count", 0)),
        internal_work_count=int(state_payload.get("internal_work_count", 0)),
        external_candidate_count=int(state_payload.get("external_candidate_count", 0)),
        dry_dispatch_count=int(state_payload.get("dry_dispatch_count", 0)),
        live_dispatch_count=int(state_payload.get("live_dispatch_count", 0)),
        refusal_count=int(state_payload.get("refusal_count", 0)),
        idle_count=int(state_payload.get("idle_count", 0)),
        panic_count=int(state_payload.get("panic_count", 0)),
        stop_reason=stop_reason,
        top_selected_task_types=task_types[:10],
        notable_refusals=refusals,
        incidents=incidents,
        proof_refs=[str(field_run_dir(field_run_id, base=base))],
        receipt_hashes=receipt_hashes,
        operator_summary=" ".join(summary_parts),
        verdict=verdict,
    ).with_hash()
    write_wake_report(report, base=base)
    return report
