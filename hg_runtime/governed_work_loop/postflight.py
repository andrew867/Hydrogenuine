"""Governed work loop postflight."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.governed_work_loop.schema import STORE_ROOT, now_iso

POSTFLIGHT_DIR = STORE_ROOT / "postflights"


@dataclass
class GovernedWorkLoopPostflight:
    postflight_id: str
    run_id: str
    verdict: str
    observed_iterations: int
    work_receipt_refs: tuple[str, ...]
    internal_work_completed: bool
    external_candidate_prepared: bool
    out_of_envelope_refused: bool
    dry_dispatch_recorded: bool
    live_dispatch_refused: bool
    external_side_effect_count: int
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "postflight_id": self.postflight_id,
            "run_id": self.run_id,
            "verdict": self.verdict,
            "observed_iterations": self.observed_iterations,
            "work_receipt_refs": list(self.work_receipt_refs),
            "internal_work_completed": self.internal_work_completed,
            "external_candidate_prepared": self.external_candidate_prepared,
            "out_of_envelope_refused": self.out_of_envelope_refused,
            "dry_dispatch_recorded": self.dry_dispatch_recorded,
            "live_dispatch_refused": self.live_dispatch_refused,
            "external_side_effect_count": self.external_side_effect_count,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> GovernedWorkLoopPostflight:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return GovernedWorkLoopPostflight(**{**self.__dict__, "hash": compute_record_hash(body)})


def write_postflight(postflight: GovernedWorkLoopPostflight) -> Path:
    POSTFLIGHT_DIR.mkdir(parents=True, exist_ok=True)
    pf = postflight.with_hash()
    path = POSTFLIGHT_DIR / f"{pf.run_id}.json"
    path.write_text(json.dumps(pf.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_postflight(run_id: str) -> GovernedWorkLoopPostflight | None:
    path = POSTFLIGHT_DIR / f"{run_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return GovernedWorkLoopPostflight(
        postflight_id=data["postflight_id"],
        run_id=data["run_id"],
        verdict=data["verdict"],
        observed_iterations=int(data.get("observed_iterations", 0)),
        work_receipt_refs=tuple(data.get("work_receipt_refs") or ()),
        internal_work_completed=bool(data.get("internal_work_completed")),
        external_candidate_prepared=bool(data.get("external_candidate_prepared")),
        out_of_envelope_refused=bool(data.get("out_of_envelope_refused")),
        dry_dispatch_recorded=bool(data.get("dry_dispatch_recorded")),
        live_dispatch_refused=bool(data.get("live_dispatch_refused")),
        external_side_effect_count=int(data.get("external_side_effect_count", 0)),
        created_at=data["created_at"],
        hash=data.get("hash"),
    )
