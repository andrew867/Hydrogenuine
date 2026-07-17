"""YSR proof summaries — observation receipts."""

from __future__ import annotations

from typing import Any

from hg_runtime.yawn.types import ResyncResult, YawnCycle


def build_yawn_report(
    *,
    cycle: YawnCycle,
    resync: ResyncResult,
    event_types_emitted: list[str],
) -> dict[str, Any]:
    return {
        "schema": "ysr-yawn-report",
        "schema_version": "1.0",
        "cycle_id": cycle.cycle_id,
        "agent_id": cycle.agent_id,
        "result_status": cycle.result_status,
        "event_lag_count": cycle.event_lag_count,
        "scratch_cleared_keys": cycle.scratch_cleared_keys,
        "resync_ok": resync.ok,
        "event_log_mutated": resync.event_log_mutated,
        "authority_freshened": resync.authority_freshened,
        "receipts_deleted": resync.receipts_deleted,
        "stale_proposals_invalidated": resync.stale_proposals_invalidated,
        "events_emitted": event_types_emitted,
        "observation_only": True,
    }


__all__ = ["build_yawn_report"]
