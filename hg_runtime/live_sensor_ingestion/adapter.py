"""SEN-LIVE runtime adapter — fake sink only; no live sensor connection."""

from __future__ import annotations

from typing import Any

from hg_core.sen_live.config import sen_fake_sink_only, sen_refuse_live_sensor_connection
from hg_core.sen_live.errors import REFUSED_LIVE_SENSOR_CONNECTION, SEN_COMMIT_FAKE_SINK
from hg_core.sen_live.no_authority import advisory_only_marker
from hg_runtime.live_sensor_ingestion.types import FIXTURE_CLOCK, SensorIngestReceipt, SensorObservationCandidate


def stage_to_fake_sink(
    candidate: SensorObservationCandidate,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Stage sensor observation candidate in fake sink; never connects to live sensor."""
    if not sen_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "sen.refused.fake_sink_disabled",
            "live_sensor_connection": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sen.advisory.request_staged",
        "sink_type": "fake",
        "candidate_ref": candidate.candidate_id,
        "modality": candidate.modality,
        "live_sensor_connection": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def commit_to_fake_sink(
    receipt: SensorIngestReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Commit sensor ingest receipt to fake sink; never connects to live sensor."""
    if not sen_refuse_live_sensor_connection():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_LIVE_SENSOR_CONNECTION,
            "live_sensor_connection": False,
        }

    if not sen_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "sen.refused.fake_sink_disabled",
            "live_sensor_connection": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": SEN_COMMIT_FAKE_SINK,
        "sink_type": "fake",
        "receipt_ref": receipt.receipt_id,
        "modality": receipt.modality,
        "live_sensor_connection": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["commit_to_fake_sink", "stage_to_fake_sink"]
