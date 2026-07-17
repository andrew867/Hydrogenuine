"""SRP-LIVE TEP emission — SRP apply plans are not permits."""

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

SOURCE_ORGAN = "SRP"


def fence_live_srp_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "srp:live:rtc:apply_emit",
        organ=SOURCE_ORGAN,
        reason="SRP live RTC apply emission uses fixture adapter only",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_apply_plan(plan_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(
        plan_dict,
        source_organ=SOURCE_ORGAN,
        claim_type="SRP_APPLY_PLAN",
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:op:fixture",
        scope_ref=str(plan_dict.get("repair_id", "srp:fixture")),
    )


def run_srp_fixture_emission(result: dict[str, Any]) -> dict[str, object]:
    wrapped = attach_translation_envelope_to_result(
        result,
        source_organ=SOURCE_ORGAN,
        claim_type="SRP_APPLY_PLAN",
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="SRP_APPLY_PLAN",
        claim_id="claim:srp:apply-fixture",
        structured_value={"phase": "plan", "is_permit": False},
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:op:fixture",
        scope_ref="srp:fixture",
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "is_permit": False,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_srp_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_apply_plan",
    "fence_live_srp_emission",
    "run_srp_fixture_emission",
]
