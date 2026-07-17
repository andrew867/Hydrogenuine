"""OEA-TER-LIVE runtime adapter — fake sink only; no live external actions."""

from __future__ import annotations

from typing import Any

from hg_core.oea_ter_live.config import oea_ter_fake_sink_only, oea_ter_refuse_live_actions
from hg_core.oea_ter_live.errors import OEA_TER_COMMIT_FAKE_SINK, REFUSED_LIVE_ACTION
from hg_core.oea_ter_live.no_authority import advisory_only_marker
from hg_runtime.live_oea_ter_bridge.types import FIXTURE_CLOCK, LiveActionCandidate, LiveActionReceipt


def request_to_fake_sink(
    candidate: LiveActionCandidate,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Stage dispatch candidate in fake sink; never performs live action."""
    if not oea_ter_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "oea_ter.refused.fake_sink_disabled",
            "live_action_performed": False,
            "oea_ter_called": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "oea_ter.advisory.request_staged",
        "sink_type": "fake",
        "candidate_ref": candidate.candidate_id,
        "external_surface": candidate.external_surface,
        "live_action_performed": False,
        "oea_ter_called": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def commit_to_fake_sink(
    receipt: LiveActionReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Commit dispatch receipt to fake sink; never performs live action."""
    if not oea_ter_refuse_live_actions():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_LIVE_ACTION,
            "live_action_performed": False,
            "oea_ter_called": False,
        }

    if not oea_ter_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "oea_ter.refused.fake_sink_disabled",
            "live_action_performed": False,
            "oea_ter_called": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": OEA_TER_COMMIT_FAKE_SINK,
        "sink_type": "fake",
        "receipt_ref": receipt.receipt_id,
        "external_surface": receipt.external_surface,
        "live_action_performed": False,
        "oea_ter_called": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["commit_to_fake_sink", "request_to_fake_sink"]
