"""MEM-LIVE TEP emission — memory write candidates are not permits."""

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

SOURCE_ORGAN = "MEM"


def fence_live_memory_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "mem:live:rtc:mutation_emit",
        organ=SOURCE_ORGAN,
        reason="MEM live RTC memory emission uses fixture adapter only",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_write_candidate(candidate_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(
        candidate_dict,
        source_organ=SOURCE_ORGAN,
        claim_type="MEMORY_MUTATION_CANDIDATE",
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref=str(candidate_dict.get("operator_ref", "iam:op:fixture")),
        scope_ref=str(candidate_dict.get("memory_key", "mem:fixture")),
    )


def run_mem_fixture_emission(result: dict[str, Any]) -> dict[str, object]:
    wrapped = attach_translation_envelope_to_result(
        result,
        source_organ=SOURCE_ORGAN,
        claim_type="MEMORY_MUTATION_CANDIDATE",
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="MEMORY_MUTATION_CANDIDATE",
        claim_id="claim:mem:mutation-fixture",
        structured_value={"mutation_kind": "write", "is_permit": False},
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:op:fixture",
        scope_ref="mem:fixture",
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "is_permit": False,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_memory_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_write_candidate",
    "fence_live_memory_emission",
    "run_mem_fixture_emission",
]
