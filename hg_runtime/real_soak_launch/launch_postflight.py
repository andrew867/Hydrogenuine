"""Soak launch postflight."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, soak_dir, now_iso


@dataclass
class SoakLaunchPostflight:
    postflight_id: str
    soak_id: str
    verdict: str
    live_posts_used: int
    external_side_effect_count: int
    wake_report_ref: str
    field_run_postflight_ref: str
    infrastructure_only: bool
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "postflight_id": self.postflight_id,
            "soak_id": self.soak_id,
            "verdict": self.verdict,
            "live_posts_used": self.live_posts_used,
            "external_side_effect_count": self.external_side_effect_count,
            "wake_report_ref": self.wake_report_ref,
            "field_run_postflight_ref": self.field_run_postflight_ref,
            "infrastructure_only": self.infrastructure_only,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> SoakLaunchPostflight:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return SoakLaunchPostflight(**{**self.__dict__, "hash": compute_record_hash(body)})


def write_postflight(pf: SoakLaunchPostflight, *, base: Path | None = None) -> Path:
    root = soak_dir(pf.soak_id, base=base)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "postflight.json"
    path.write_text(json.dumps(pf.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_postflight(soak_id: str, *, base: Path | None = None) -> SoakLaunchPostflight | None:
    path = soak_dir(soak_id, base=base) / "postflight.json"
    if not path.is_file():
        return None
    return SoakLaunchPostflight(**json.loads(path.read_text(encoding="utf-8")))
