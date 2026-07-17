"""REB-RESTORE-LIVE runtime adapter — fake sink only; no live checkpoint restore."""

from __future__ import annotations

from typing import Any

from hg_core.reb_restore_live.config import reb_restore_fake_sink_only, reb_restore_refuse_live_restore
from hg_core.reb_restore_live.errors import REB_RESTORE_COMMIT_FAKE_SINK, REFUSED_LIVE_RESTORE
from hg_core.reb_restore_live.no_authority import advisory_only_marker
from hg_runtime.live_reentry_restore.types import FIXTURE_CLOCK, RestoreCandidate, RestoreReceipt


def stage_to_fake_sink(candidate: RestoreCandidate, *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    if not reb_restore_fake_sink_only():
        return {**advisory_only_marker(), "status": "refused", "reason_code": "reb_restore.refused.fake_sink_disabled", "live_restore_performed": False}
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": "reb_restore.advisory.request_staged",
        "sink_type": "fake", "candidate_ref": candidate.candidate_id, "restore_kind": candidate.restore_kind,
        "live_restore_performed": False, "live_action_performed": False, "permission_granted": False, "observed_at": observed_at,
    }


def commit_to_fake_sink(receipt: RestoreReceipt, *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    if not reb_restore_refuse_live_restore():
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_LIVE_RESTORE, "live_restore_performed": False}
    if not reb_restore_fake_sink_only():
        return {**advisory_only_marker(), "status": "refused", "reason_code": "reb_restore.refused.fake_sink_disabled", "live_restore_performed": False}
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": REB_RESTORE_COMMIT_FAKE_SINK,
        "sink_type": "fake", "receipt_ref": receipt.receipt_id, "restore_kind": receipt.restore_kind,
        "live_restore_performed": False, "live_action_performed": False, "permission_granted": False, "observed_at": observed_at,
    }


__all__ = ["commit_to_fake_sink", "stage_to_fake_sink"]
