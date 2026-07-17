"""Scan replay results for mismatch with recorded verdict."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.agent_immune_system.finding import build_finding
from hg_runtime.agent_immune_system.hashing import record_hash


def scan_replay(bundle_dir: Path) -> list[dict]:
    findings: list[dict] = []
    bundle_dir = Path(bundle_dir)
    label = bundle_dir.name
    replay_path = bundle_dir / "replay_result.json"
    if not replay_path.exists():
        return findings

    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    stored_ok = replay.get("ok")
    stored_hash = replay.get("replay_hash") or replay.get("replay_input_hash")

    recomputed = record_hash({k: v for k, v in replay.items() if k not in ("replay_hash", "replay_input_hash")})
    if stored_hash and stored_hash != recomputed and not replay.get("replay_hash_is_stable"):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-replay-mismatch",
                finding_type="replay_mismatch",
                severity="RED",
                safe_action="RESTRICT",
                surface=str(replay_path),
                blocks_green=True,
            )
        )

    if replay.get("forced_mismatch"):
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-replay-forced-mismatch",
                finding_type="replay_mismatch",
                severity="RED",
                safe_action="RESTRICT",
                surface=str(replay_path),
                blocks_green=True,
            )
        )

    if stored_ok is False:
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-replay-failed",
                finding_type="replay_mismatch",
                severity="RED",
                safe_action="RESTRICT",
                surface=str(replay_path),
                blocks_green=True,
            )
        )

    return findings
