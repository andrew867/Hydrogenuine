"""GMG-LIVE runtime adapter — fake sink only; no live grants."""

from __future__ import annotations

from typing import Any

from hg_core.gmg_live.config import gmg_fake_sink_only, gmg_refuse_live_grants
from hg_core.gmg_live.errors import GMG_COMMIT_FAKE_SINK, REFUSED_LIVE_GRANT
from hg_core.gmg_live.no_authority import advisory_only_marker
from hg_runtime.grant_authority_live.types import FIXTURE_CLOCK, GrantCandidate, GrantReceipt


def request_to_fake_sink(
    candidate: GrantCandidate,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Stage grant candidate in fake sink; never performs live grant."""
    if not gmg_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "gmg.refused.fake_sink_disabled",
            "live_grant_performed": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "gmg.advisory.request_staged",
        "sink_type": "fake",
        "candidate_ref": candidate.candidate_id,
        "grant_type": candidate.grant_type,
        "live_grant_performed": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def commit_to_fake_sink(
    receipt: GrantReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Commit grant receipt to fake sink; never performs live grant."""
    if not gmg_refuse_live_grants():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_LIVE_GRANT,
            "live_grant_performed": False,
        }

    if not gmg_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "gmg.refused.fake_sink_disabled",
            "live_grant_performed": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": GMG_COMMIT_FAKE_SINK,
        "sink_type": "fake",
        "receipt_ref": receipt.receipt_id,
        "grant_type": receipt.grant_type,
        "live_grant_performed": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["commit_to_fake_sink", "request_to_fake_sink"]
