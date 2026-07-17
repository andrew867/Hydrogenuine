"""External action quota tracking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hg_runtime.governed_work_loop.schema import STORE_ROOT, load_governed_work_policy

QUOTA_DIR = STORE_ROOT / "quotas"


@dataclass
class ExternalActionQuota:
    quota_id: str
    max_candidates: int
    max_dry_dispatches: int
    max_live_dispatches: int
    candidates_used: int = 0
    dry_dispatches_used: int = 0
    live_dispatches_used: int = 0

    def to_payload(self) -> dict:
        return {
            "quota_id": self.quota_id,
            "max_candidates": self.max_candidates,
            "max_dry_dispatches": self.max_dry_dispatches,
            "max_live_dispatches": self.max_live_dispatches,
            "candidates_used": self.candidates_used,
            "dry_dispatches_used": self.dry_dispatches_used,
            "live_dispatches_used": self.live_dispatches_used,
        }

    def may_create_candidate(self) -> bool:
        return self.candidates_used < self.max_candidates

    def may_dry_dispatch(self) -> bool:
        return self.dry_dispatches_used < self.max_dry_dispatches

    def may_live_dispatch(self) -> bool:
        return self.max_live_dispatches > 0 and self.live_dispatches_used < self.max_live_dispatches

    def record_candidate(self) -> None:
        self.candidates_used += 1
        _persist(self)

    def record_dry_dispatch(self) -> None:
        self.dry_dispatches_used += 1
        _persist(self)

    def record_live_dispatch(self) -> None:
        self.live_dispatches_used += 1
        _persist(self)


def _persist(quota: ExternalActionQuota) -> None:
    QUOTA_DIR.mkdir(parents=True, exist_ok=True)
    (QUOTA_DIR / f"{quota.quota_id}.json").write_text(json.dumps(quota.to_payload(), indent=2) + "\n", encoding="utf-8")


def reset_quota_for_run(run_id: str) -> ExternalActionQuota:
    q = ExternalActionQuota(quota_id=run_id, max_candidates=10, max_dry_dispatches=10, max_live_dispatches=0)
    _persist(q)
    return q


def load_or_create_quota(quota_id: str = "default") -> ExternalActionQuota:
    path = QUOTA_DIR / f"{quota_id}.json"
    policy = load_governed_work_policy()
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExternalActionQuota(
            quota_id=data["quota_id"],
            max_candidates=int(data["max_candidates"]),
            max_dry_dispatches=int(data["max_dry_dispatches"]),
            max_live_dispatches=int(data["max_live_dispatches"]),
            candidates_used=int(data.get("candidates_used", 0)),
            dry_dispatches_used=int(data.get("dry_dispatches_used", 0)),
            live_dispatches_used=int(data.get("live_dispatches_used", 0)),
        )
    q = ExternalActionQuota(
        quota_id=quota_id,
        max_candidates=5,
        max_dry_dispatches=5,
        max_live_dispatches=int(policy.get("max_live_dispatches_default", 0)),
    )
    _persist(q)
    return q
