"""ERB TEP-D fixture emission — external relation is not permission."""

from __future__ import annotations

from typing import Any

from hg_runtime.external_relation_boundary.evaluator import route_relation_bundle
from hg_runtime.external_relation_boundary.fixtures import load_fixture_bundles
from hg_runtime.external_relation_boundary.types import FIXTURE_CLOCK, context_from_fixture, entity_from_fixture
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "ERB"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "erb:live:rtc:relation_emit",
        organ=SOURCE_ORGAN,
        reason="ERB live RTC relation emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_relation_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="BOUNDARY_RECEIPT")


def run_erb_fixture_emission() -> dict[str, object]:
    bundles = load_fixture_bundles()
    bundle = bundles[0] if bundles else {"entity": {}, "context": {}}
    entity = entity_from_fixture(bundle["entity"])
    context = context_from_fixture(bundle["context"], entity_ref_id=entity.entity_ref_id)
    result = route_relation_bundle(entity, context, observed_at=FIXTURE_CLOCK)
    wrapped = attach_translation_envelope_to_result(result, source_organ=SOURCE_ORGAN, claim_type="BOUNDARY_RECEIPT")
    receipt = result.get("receipt")
    if isinstance(receipt, dict):
        wrapped["relation_receipt_envelope"] = emit_fixture_relation_receipt(receipt)["translation_envelope"]
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="BOUNDARY_RECEIPT",
        claim_id="claim:erb:relation-fixture",
        structured_value={"relation_is_advisory_only": True},
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
    "emit_fixture_relation_receipt",
    "fence_live_rtc_emission",
    "run_erb_fixture_emission",
]
