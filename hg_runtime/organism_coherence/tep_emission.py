"""H8 TEP-D fixture emission — organism coherence is not authority."""

from __future__ import annotations

from typing import Any

from hg_runtime.organism_coherence import FIXTURE_CLOCK, load_organism_fixtures, process_organism_bundle
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "H8"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "h8:live:rtc:coherence_emit",
        organ=SOURCE_ORGAN,
        reason="H8 live RTC coherence emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_coherence_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="BOUNDARY_RECEIPT")


def run_h8_fixture_emission() -> dict[str, object]:
    bundles = load_organism_fixtures()
    bundle = next((b for b in bundles if b["bundle_id"] == "h8-valid-coherence"), bundles[0])
    result = process_organism_bundle(bundle, observed_at=FIXTURE_CLOCK)
    wrapped = attach_translation_envelope_to_result(
        result, source_organ=SOURCE_ORGAN, claim_type="BOUNDARY_RECEIPT", receipt_key="coherence_receipt"
    )
    receipt = result.get("coherence_receipt")
    if isinstance(receipt, dict):
        wrapped["coherence_receipt_envelope"] = emit_fixture_coherence_receipt(receipt)["translation_envelope"]
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="BOUNDARY_RECEIPT",
        claim_id="claim:h8:coherence-fixture",
        structured_value={"organism_coherence": True, "not_authority": True},
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
    "emit_fixture_coherence_receipt",
    "fence_live_rtc_emission",
    "run_h8_fixture_emission",
]
