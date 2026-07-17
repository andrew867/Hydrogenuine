"""RIB-SPAWN-LIVE TEP emission — spawn plans are not permits."""

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

SOURCE_ORGAN = "RIB_SPAWN"


def fence_live_spawn_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "rib_spawn:live:rtc:spawn_emit",
        organ=SOURCE_ORGAN,
        reason="RIB-SPAWN live RTC spawn emission uses fixture adapter only",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_spawn_plan(plan_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(
        plan_dict,
        source_organ=SOURCE_ORGAN,
        claim_type="CHILD_SPAWN_PLAN",
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref=str(plan_dict.get("child_iam_ref", "iam:child:fixture")),
        scope_ref=str(plan_dict.get("parent_iam_ref", "iam:parent:fixture")),
    )


def run_rib_spawn_fixture_emission(result: dict[str, Any]) -> dict[str, object]:
    wrapped = attach_translation_envelope_to_result(
        result,
        source_organ=SOURCE_ORGAN,
        claim_type="CHILD_SPAWN_PLAN",
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="CHILD_SPAWN_PLAN",
        claim_id="claim:rib:spawn-fixture",
        structured_value={"live_spawn_performed": False, "is_permit": False},
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:child:fixture",
        scope_ref="iam:parent:fixture",
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "is_permit": False,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_spawn_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_spawn_plan",
    "fence_live_spawn_emission",
    "run_rib_spawn_fixture_emission",
]
