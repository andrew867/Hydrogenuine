"""ARB TEP-D fixture emission — routing is not permission."""

from __future__ import annotations

from typing import Any

from hg_runtime.agency_routing_boundary.evaluator import analyze_fixture_bundle
from hg_runtime.agency_routing_boundary.fixtures import STATIC_SIGNAL_FIXTURES
from hg_runtime.agency_routing_boundary.types import FIXTURE_CLOCK
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "ARB"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "arb:live:rtc:route_emit",
        organ=SOURCE_ORGAN,
        reason="ARB live RTC route emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_route_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="ROUTE_DECISION")


def run_arb_fixture_emission() -> dict[str, object]:
    bundle = {"bundle_id": "arb-tep-d-fixture", "signals": list(STATIC_SIGNAL_FIXTURES[:2])}
    result = analyze_fixture_bundle(bundle, observed_at=FIXTURE_CLOCK)
    wrapped = attach_translation_envelope_to_result(result, source_organ=SOURCE_ORGAN, claim_type="ROUTE_DECISION")
    route_results = result.get("results", [])
    if isinstance(route_results, list) and route_results:
        first = route_results[0]
        receipt = first.get("receipt") if isinstance(first, dict) else None
        if isinstance(receipt, dict):
            wrapped["route_receipt_envelope"] = emit_fixture_route_receipt(receipt)["translation_envelope"]
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="ROUTE_DECISION",
        claim_id="claim:arb:route-fixture",
        structured_value={"route_class": "operator_review", "advisory_only": True},
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
    "emit_fixture_route_receipt",
    "fence_live_rtc_emission",
    "run_arb_fixture_emission",
]
