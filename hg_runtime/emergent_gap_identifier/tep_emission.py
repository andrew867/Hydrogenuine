"""EGI TEP-D fixture emission — infrastructure need is not a tool grant."""

from __future__ import annotations

from typing import Any

from hg_runtime.emergent_gap_identifier.packet_surface import render_packet_surface_fixture
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "EGI"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "egi:live:rtc:gap_emit",
        organ=SOURCE_ORGAN,
        reason="EGI live RTC gap emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_gap_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="PRIORITY_SCORE")


def run_egi_fixture_emission() -> dict[str, object]:
    result = render_packet_surface_fixture()
    wrapped = attach_translation_envelope_to_result(result, source_organ=SOURCE_ORGAN, claim_type="PRIORITY_SCORE")
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="PRIORITY_SCORE",
        claim_id="claim:egi:gap-fixture",
        structured_value={"proposal_only": True, "may_grant_tools": False},
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "proposal_only": True,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_rtc_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_gap_receipt",
    "fence_live_rtc_emission",
    "run_egi_fixture_emission",
]
