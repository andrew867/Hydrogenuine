"""IMB TEP-D fixture emission — consensus is not authority."""

from __future__ import annotations

from typing import Any

from hg_runtime.internal_mediation_boundary.evaluator import mediate_claim_bundle
from hg_runtime.internal_mediation_boundary.fixtures import load_fixture_bundles
from hg_runtime.internal_mediation_boundary.types import FIXTURE_CLOCK
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "IMB"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "imb:live:rtc:mediation_emit",
        organ=SOURCE_ORGAN,
        reason="IMB live RTC mediation emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_mediation_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="BOUNDARY_RECEIPT")


def run_imb_fixture_emission() -> dict[str, object]:
    bundles = load_fixture_bundles()
    bundle = bundles[0] if bundles else {"claims": []}
    from hg_runtime.internal_mediation_boundary.fixtures import claims_from_bundle

    claims = claims_from_bundle(bundle)
    result = mediate_claim_bundle(claims, observed_at=FIXTURE_CLOCK)
    wrapped = attach_translation_envelope_to_result(result, source_organ=SOURCE_ORGAN, claim_type="BOUNDARY_RECEIPT")
    receipts = result.get("receipts", [])
    if isinstance(receipts, list) and receipts:
        first = receipts[0]
        if isinstance(first, dict):
            wrapped["mediation_receipt_envelope"] = emit_fixture_mediation_receipt(first)["translation_envelope"]
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="BOUNDARY_RECEIPT",
        claim_id="claim:imb:mediation-fixture",
        structured_value={"consensus_is_not_authority": True},
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "consensus_is_not_authority": True,
        "fixture_result": wrapped,
        "sample_emission": sample,
        "live_fenced": fence_live_rtc_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_mediation_receipt",
    "fence_live_rtc_emission",
    "run_imb_fixture_emission",
]
