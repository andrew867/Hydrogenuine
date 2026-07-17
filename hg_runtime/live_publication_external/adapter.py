"""PUB-EXT-LIVE runtime adapter — fake sink only; no live external action."""

from __future__ import annotations

from typing import Any

from hg_core.pub_ext_live.config import pub_ext_fake_sink_only, pub_ext_refuse_live_external_action
from hg_core.pub_ext_live.errors import PUB_EXT_COMMIT_FAKE_SINK, REFUSED_LIVE_EXTERNAL_ACTION
from hg_core.pub_ext_live.no_authority import advisory_only_marker
from hg_runtime.live_publication_external.types import FIXTURE_CLOCK, PublicationCandidate, PublicationReceipt


def stage_to_fake_sink(candidate: PublicationCandidate, *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    if not pub_ext_fake_sink_only():
        return {**advisory_only_marker(), "status": "refused", "reason_code": "pub_ext.refused.fake_sink_disabled", "live_external_action": False}
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": "pub_ext.advisory.request_staged",
        "sink_type": "fake", "candidate_ref": candidate.candidate_id, "release_kind": candidate.release_kind,
        "published": False, "live_external_action": False, "permission_granted": False, "observed_at": observed_at,
    }


def commit_to_fake_sink(receipt: PublicationReceipt, *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    if not pub_ext_refuse_live_external_action():
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_LIVE_EXTERNAL_ACTION, "live_external_action": False}
    if not pub_ext_fake_sink_only():
        return {**advisory_only_marker(), "status": "refused", "reason_code": "pub_ext.refused.fake_sink_disabled", "live_external_action": False}
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": PUB_EXT_COMMIT_FAKE_SINK,
        "sink_type": "fake", "receipt_ref": receipt.receipt_id, "release_kind": receipt.release_kind,
        "published": False, "live_external_action": False, "permission_granted": False, "observed_at": observed_at,
    }


__all__ = ["commit_to_fake_sink", "stage_to_fake_sink"]
