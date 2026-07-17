"""ALOOP-LIVE TEP emission — loop leases are not permits."""

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

SOURCE_ORGAN = "ALOOP"


def fence_live_loop_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "aloop:live:rtc:loop_emit",
        organ=SOURCE_ORGAN,
        reason="ALOOP live RTC loop emission uses fixture adapter only",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_loop_lease(lease_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(
        lease_dict,
        source_organ=SOURCE_ORGAN,
        claim_type="LOOP_SUPERVISOR_LEASE",
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref=str(lease_dict.get("operator_ref", "iam:op:fixture")),
        scope_ref=str(lease_dict.get("loop_scope", "loop:fixture")),
    )


def run_aloop_fixture_emission(result: dict[str, Any]) -> dict[str, object]:
    wrapped = attach_translation_envelope_to_result(
        result,
        source_organ=SOURCE_ORGAN,
        claim_type="LOOP_SUPERVISOR_LEASE",
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="LOOP_SUPERVISOR_LEASE",
        claim_id="claim:aloop:loop-fixture",
        structured_value={"live_loop_started": False, "is_permit": False},
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:op:fixture",
        scope_ref="loop:fixture",
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "is_permit": False,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_loop_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_loop_lease",
    "fence_live_loop_emission",
    "run_aloop_fixture_emission",
]
