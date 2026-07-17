"""IPB TEP-D fixture emission — local autonomy is not permission."""

from __future__ import annotations

from typing import Any

from hg_runtime.internal_power_boundary.evaluator import analyze_fixture_bundle
from hg_runtime.internal_power_boundary.fixtures import FIXTURE_DECISION_LOGS
from hg_runtime.internal_power_boundary.types import FIXTURE_CLOCK
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "IPB"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "ipb:live:rtc:autonomy_emit",
        organ=SOURCE_ORGAN,
        reason="IPB live RTC autonomy emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_autonomy_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="DRIVE_SIGNAL")


def run_ipb_fixture_emission() -> dict[str, object]:
    bundle = {
        "bundle_id": "ipb-tep-d-fixture",
        "decisions": [row["decision"] for row in FIXTURE_DECISION_LOGS[:2]],
    }
    result = analyze_fixture_bundle(bundle, observed_at=FIXTURE_CLOCK)
    wrapped = attach_translation_envelope_to_result(result, source_organ=SOURCE_ORGAN, claim_type="DRIVE_SIGNAL")
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="DRIVE_SIGNAL",
        claim_id="claim:ipb:autonomy-fixture",
        structured_value={"local_autonomy": True, "not_permission": True},
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_rtc_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_autonomy_receipt",
    "fence_live_rtc_emission",
    "run_ipb_fixture_emission",
]
