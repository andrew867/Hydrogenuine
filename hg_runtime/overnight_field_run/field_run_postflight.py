"""Field run postflight."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.overnight_field_run.schema import FieldRunMode, OvernightFieldRunVerdict, field_run_dir, load_field_run_policy, now_iso


@dataclass
class FieldRunPostflight:
    postflight_id: str
    field_run_id: str
    mode: str
    verdict: str
    turn_count: int
    task_selection_count: int
    governed_work_count: int
    external_side_effect_count: int
    background_process_survives: bool
    wake_report_ref: str
    continuity_audit_ref: str
    stop_requested: bool
    panic_requested: bool
    infrastructure_only: bool
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "postflight_id": self.postflight_id,
            "field_run_id": self.field_run_id,
            "mode": self.mode,
            "verdict": self.verdict,
            "turn_count": self.turn_count,
            "task_selection_count": self.task_selection_count,
            "governed_work_count": self.governed_work_count,
            "external_side_effect_count": self.external_side_effect_count,
            "background_process_survives": self.background_process_survives,
            "wake_report_ref": self.wake_report_ref,
            "continuity_audit_ref": self.continuity_audit_ref,
            "stop_requested": self.stop_requested,
            "panic_requested": self.panic_requested,
            "infrastructure_only": self.infrastructure_only,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> FieldRunPostflight:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return FieldRunPostflight(**{**self.__dict__, "hash": compute_record_hash(body)})


def write_postflight(postflight: FieldRunPostflight, *, base: Path | None = None) -> Path:
    root = field_run_dir(postflight.field_run_id, base=base)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "postflight.json"
    path.write_text(json.dumps(postflight.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_postflight(field_run_id: str, *, base: Path | None = None) -> FieldRunPostflight | None:
    path = field_run_dir(field_run_id, base=base) / "postflight.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return FieldRunPostflight(**data)


def resolve_verdict(
    *,
    mode: str,
    session_verdict: str,
    turn_count: int,
    external_side_effects: int,
    continuity_verdict: str,
    elapsed_seconds: float = 0.0,
) -> str:
    import os

    policy = load_field_run_policy()
    min_elapsed = float(policy.get("min_elapsed_seconds_for_overnight_complete", 3600))
    fast_turns = os.environ.get("HG_HANDS_OFF_FAST_TURNS") == "1"

    if external_side_effects > 0:
        return OvernightFieldRunVerdict.RED_EXTERNAL_SIDE_EFFECT.value
    if continuity_verdict.startswith("RED_"):
        return continuity_verdict
    if session_verdict.startswith("RED_"):
        return session_verdict
    if mode == FieldRunMode.INFRASTRUCTURE_SMOKE.value:
        return OvernightFieldRunVerdict.GREEN_INFRASTRUCTURE_READY.value
    if (
        mode == FieldRunMode.OPERATOR_FIELD_RUN.value
        and turn_count >= 10
        and elapsed_seconds >= min_elapsed
        and not fast_turns
    ):
        return OvernightFieldRunVerdict.GREEN_FIELD_RUN_COMPLETE.value
    if mode == FieldRunMode.OPERATOR_FIELD_RUN.value:
        return OvernightFieldRunVerdict.YELLOW_OPERATOR_STOPPED.value
    return OvernightFieldRunVerdict.GREEN_INFRASTRUCTURE_READY.value
