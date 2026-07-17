"""
Wake/sleep bookkeeping for automation sessions.

This module records lightweight wake receipts so the system can measure
time between runs and trigger sleep GC after completed cron runs.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.temporal_changelog import record_major_disruption_once
from hg_core.job_registry import get_compatible_session_targets
from hg_gateway.operational_state_ledger import load_operational_json_state, save_operational_json_state


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def record_wake(
    *,
    workspace_root: Path,
    task_name: str,
    session_id: str,
    output_mode: str,
    wake_packet: str,
    memory_profile: Optional[str],
    dag_inputs: Optional[Dict[str, Any]] = None,
) -> None:
    """Write wake_receipt.json and append to wake_log.jsonl."""
    compatible_targets = get_compatible_session_targets(task_name) or [session_id]
    if session_id not in compatible_targets:
        compatible_targets.insert(0, session_id)
    agent_id = session_id.replace("automation-", "", 1)
    memory_dirs: list[Path] = []
    seen_dirs: set[Path] = set()
    for target in compatible_targets:
        target_agent_id = target.replace("automation-", "", 1)
        memory_dir = workspace_root / "memory" / "automation" / f"automation-{target_agent_id}"
        if memory_dir in seen_dirs:
            continue
        seen_dirs.add(memory_dir)
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_dirs.append(memory_dir)
    prior_receipt = None
    try:
        for memory_dir in memory_dirs:
            receipt_path = memory_dir / "wake_receipt.json"
            if receipt_path.exists():
                prior_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                break
    except Exception:
        prior_receipt = None
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    receipt = {
        "at": now,
        "task": task_name,
        "session_id": session_id,
        "output_mode": output_mode,
        "memory_profile": memory_profile or "",
        "wake_packet_hash": _hash_text(wake_packet or ""),
        "dag_inputs_present": bool(dag_inputs),
    }
    for memory_dir in memory_dirs:
        try:
            (memory_dir / "wake_receipt.json").write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            continue
    for target in compatible_targets:
        try:
            state = load_operational_json_state(
                workspace_root,
                state_key=f"identity_continuity_state:{target}",
            )
            payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
            payload.update(
                {
                    "wake_receipt_present": True,
                    "last_wake_at": now,
                    "wake_receipt_recorded_at": now,
                    "wake_receipt_path": str(memory_dir / "wake_receipt.json"),
                    "wake_packet_hash": receipt["wake_packet_hash"],
                    "wake_receipt": receipt,
                }
            )
            save_operational_json_state(
                workspace_root,
                state_key=f"identity_continuity_state:{target}",
                payload=payload,
            )
        except Exception:
            continue

    try:
        log_path = workspace_root / "memory" / "overseer" / "wake_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    except OSError:
        pass

    _maybe_record_abnormal_wake_gap(
        workspace_root=workspace_root,
        task_name=task_name,
        agent_id=agent_id,
        previous_receipt=prior_receipt,
        current_receipt=receipt,
    )


def _expected_wake_gap_ms(task_name: str) -> int:
    try:
        from hg_core.wrappers.cron_health_monitor import EXPECTED_INTERVALS

        interval = EXPECTED_INTERVALS["every"].get(task_name)
        if isinstance(interval, int) and interval > 0:
            return max(interval * 3, 6 * 60 * 60 * 1000)
    except Exception:
        pass
    return 6 * 60 * 60 * 1000


def _maybe_record_abnormal_wake_gap(
    *,
    workspace_root: Path,
    task_name: str,
    agent_id: str,
    previous_receipt: Optional[Dict[str, Any]],
    current_receipt: Dict[str, Any],
) -> None:
    if not previous_receipt:
        return
    prev_at = str(previous_receipt.get("at") or "").strip()
    cur_at = str(current_receipt.get("at") or "").strip()
    try:
        prev_dt = datetime.fromisoformat(prev_at.replace("Z", "+00:00"))
        cur_dt = datetime.fromisoformat(cur_at.replace("Z", "+00:00"))
    except ValueError:
        return
    gap_ms = int((cur_dt - prev_dt).total_seconds() * 1000)
    threshold_ms = _expected_wake_gap_ms(task_name)
    if gap_ms <= threshold_ms:
        return
    gap_hours = round(gap_ms / (1000 * 60 * 60), 1)
    record_major_disruption_once(
        title="Unexpected gap in activity",
        summary=f"There was a longer-than-normal pause before the next wake cycle ({gap_hours}h).",
        workspace_root=workspace_root,
        dedupe_key=f"time_jump:{task_name}",
        kind="time_jump",
        start_at=prev_at,
        end_at=cur_at,
        severity="high",
        tags=["time_jump", "wake_gap"],
        affected_entities=[agent_id],
        details={"task_name": task_name, "gap_hours": gap_hours},
        within_hours=24,
    )
