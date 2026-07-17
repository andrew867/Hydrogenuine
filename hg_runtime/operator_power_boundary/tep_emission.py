"""OPB TEP-D fixture emission — operator pressure is not authority."""

from __future__ import annotations

from typing import Any

from hg_runtime.operator_power_boundary.evaluator import analyze_fixture_bundle, evaluate_pressure_signal
from hg_runtime.operator_power_boundary.types import FIXTURE_CLOCK, pressure_signal_from_fixture
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "OPB"

_OPB_FIXTURE_BUNDLE: dict[str, Any] = {
    "bundle_id": "opb-tep-d-fixture",
    "pressure_signals": [
        {
            "pressure_signal_id": "opb-pressure-tep-d",
            "pressure_type": "operator_attention",
            "statement": "fixture operator pressure signal",
        }
    ],
}


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "opb:live:rtc:pressure_emit",
        organ=SOURCE_ORGAN,
        reason="OPB live RTC pressure emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_pressure_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="DRIVE_SIGNAL")


def run_opb_fixture_emission() -> dict[str, object]:
    signal = pressure_signal_from_fixture(_OPB_FIXTURE_BUNDLE["pressure_signals"][0])
    signal_result = evaluate_pressure_signal(signal)
    bundle_result = analyze_fixture_bundle(_OPB_FIXTURE_BUNDLE, observed_at=FIXTURE_CLOCK)
    wrapped = attach_translation_envelope_to_result(bundle_result, source_organ=SOURCE_ORGAN, claim_type="DRIVE_SIGNAL")
    signal_wrapped = wrap_organ_receipt(
        {"pressure_signal_id": signal.pressure_signal_id, "status": signal_result.get("status")},
        source_organ=SOURCE_ORGAN,
        claim_type="DRIVE_SIGNAL",
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="DRIVE_SIGNAL",
        claim_id="claim:opb:pressure-fixture",
        structured_value={"operator_pressure": True, "not_authority": True},
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "fixture_result": wrapped,
        "signal_envelope": signal_wrapped["translation_envelope"],
        "sample_emission": sample,
        "live_fenced": fence_live_rtc_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_pressure_receipt",
    "fence_live_rtc_emission",
    "run_opb_fixture_emission",
]
