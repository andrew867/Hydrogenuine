"""INFER-LIVE TEP emission — inference outputs are not permits."""

from __future__ import annotations

from typing import Any

from hg_runtime.translation_envelope_protocol.fixtures import REVIEW_RECEIPT_AUTHORITY
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "INFER"


def fence_live_inference_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "infer:live:rtc:emit",
        organ=SOURCE_ORGAN,
        reason="INFER live RTC emission uses dry-run adapter only",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_inference_output(output_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(
        output_dict,
        source_organ=SOURCE_ORGAN,
        claim_type="SIMULATION_RESULT",
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:op:fixture",
        scope_ref="inference:fixture",
    )


def run_infer_fixture_emission(result: dict[str, Any]) -> dict[str, object]:
    wrapped = attach_translation_envelope_to_result(
        result,
        source_organ=SOURCE_ORGAN,
        claim_type="SIMULATION_RESULT",
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="SIMULATION_RESULT",
        claim_id="claim:infer:fixture",
        structured_value={"inference_output": "dry-run", "is_permit": False},
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:op:fixture",
        scope_ref="inference:fixture",
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "is_permit": False,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_inference_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_inference_output",
    "fence_live_inference_emission",
    "run_infer_fixture_emission",
]
