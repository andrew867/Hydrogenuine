"""ORI TEP-D fixture emission — review receipts are not permits."""

from __future__ import annotations

from typing import Any

from hg_runtime.operator_review_intake.evaluator import process_review_queue
from hg_runtime.operator_review_intake.intake_fixtures import load_static_fixture_requests
from hg_runtime.operator_review_intake.types import FIXTURE_CLOCK
from hg_runtime.translation_envelope_protocol.fixtures import REVIEW_RECEIPT_AUTHORITY
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "ORI"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "ori:live:rtc:review_emit",
        organ=SOURCE_ORGAN,
        reason="ORI live RTC review emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_review_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(
        receipt_dict,
        source_organ=SOURCE_ORGAN,
        claim_type="OPERATOR_REVIEW_RECEIPT",
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref=str(receipt_dict.get("identity_ref", "iam:op:fixture")),
        scope_ref=str(receipt_dict.get("scope_ref", "review:fixture")),
    )


def run_ori_fixture_emission() -> dict[str, object]:
    requests = load_static_fixture_requests()[:3]
    result = process_review_queue(requests, observed_at=FIXTURE_CLOCK)
    wrapped = attach_translation_envelope_to_result(
        result, source_organ=SOURCE_ORGAN, claim_type="OPERATOR_REVIEW_RECEIPT"
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="OPERATOR_REVIEW_RECEIPT",
        claim_id="claim:ori:review-fixture",
        structured_value={"operator_action": "deferred", "is_permit": False},
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
    "emit_fixture_review_receipt",
    "fence_live_rtc_emission",
    "run_ori_fixture_emission",
]
