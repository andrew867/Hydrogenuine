"""OUX-LIVE TEP emission — operator UX receipts are not permits."""

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

SOURCE_ORGAN = "OUX"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "oux:live:rtc:console_emit",
        organ=SOURCE_ORGAN,
        reason="OUX live RTC console emission uses fixture adapter only",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_ux_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(
        receipt_dict,
        source_organ=SOURCE_ORGAN,
        claim_type="OPERATOR_REVIEW_RECEIPT",
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref=str(receipt_dict.get("operator_ref", "iam:op:fixture")),
        scope_ref=str(receipt_dict.get("scope", "review:fixture")),
    )


def run_oux_fixture_emission(result: dict[str, Any]) -> dict[str, object]:
    wrapped = attach_translation_envelope_to_result(
        result,
        source_organ=SOURCE_ORGAN,
        claim_type="OPERATOR_REVIEW_RECEIPT",
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="OPERATOR_REVIEW_RECEIPT",
        claim_id="claim:oux:console-fixture",
        structured_value={"control_kind": "approve", "is_permit": False},
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:op:fixture",
        scope_ref="review:fixture",
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "is_permit": False,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_rtc_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_ux_receipt",
    "fence_live_rtc_emission",
    "run_oux_fixture_emission",
]
