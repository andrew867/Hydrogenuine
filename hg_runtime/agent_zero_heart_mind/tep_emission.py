"""A0-HM TEP-D fixture emission — signal is not self, truth, permission, or authority."""

from __future__ import annotations

from typing import Any

from hg_runtime.agent_zero_heart_mind.evaluator import process_fixture_dict
from hg_runtime.agent_zero_heart_mind.fixtures import load_fixture_bundles
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "A0-HM"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "a0hm:live:rtc:signal_emit",
        organ=SOURCE_ORGAN,
        reason="A0-HM live RTC signal emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_non_fusion_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="BOUNDARY_RECEIPT")


def run_a0_hm_fixture_emission() -> dict[str, object]:
    bundles = load_fixture_bundles()
    bundle = bundles[0] if bundles else {"fixture": {}}
    fixture = bundle.get("fixture", bundle)
    assert isinstance(fixture, dict)
    result = process_fixture_dict(fixture)  # type: ignore[arg-type]
    wrapped = attach_translation_envelope_to_result(
        result, source_organ=SOURCE_ORGAN, claim_type="BOUNDARY_RECEIPT", receipt_key="non_fusion_receipt"
    )
    receipt = result.get("non_fusion_receipt")
    if isinstance(receipt, dict):
        wrapped["non_fusion_envelope"] = emit_fixture_non_fusion_receipt(receipt)["translation_envelope"]
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="BOUNDARY_RECEIPT",
        claim_id="claim:a0hm:signal-fixture",
        structured_value={"non_fusion": True, "not_authority": True},
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
    "emit_fixture_non_fusion_receipt",
    "fence_live_rtc_emission",
    "run_a0_hm_fixture_emission",
]
