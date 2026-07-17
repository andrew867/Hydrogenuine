"""RIB TEP-D fixture emission — inheritance is not permission."""

from __future__ import annotations

from typing import Any

from hg_runtime.reproduction_inheritance_boundary.evaluator import record_spawn_request, route_spawn_bundle
from hg_runtime.reproduction_inheritance_boundary.fixtures import load_fixture_bundles, spawn_from_bundle
from hg_runtime.reproduction_inheritance_boundary.types import FIXTURE_CLOCK
from hg_runtime.translation_envelope_protocol.organ_emission import (
    FW_QUEUE_TEP_D_LIVE,
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    fence_legacy_naked_path,
    wrap_organ_receipt,
)

SOURCE_ORGAN = "RIB"


def fence_live_rtc_emission() -> dict[str, object]:
    return fence_legacy_naked_path(
        "rib:live:rtc:spawn_emit",
        organ=SOURCE_ORGAN,
        reason="RIB live RTC spawn emission deferred",
        future_work_id=FW_QUEUE_TEP_D_LIVE,
    )


def emit_fixture_lifecycle_receipt(receipt_dict: dict[str, Any]) -> dict[str, object]:
    return wrap_organ_receipt(receipt_dict, source_organ=SOURCE_ORGAN, claim_type="INHERITANCE_PACKET")


def run_rib_fixture_emission() -> dict[str, object]:
    bundles = load_fixture_bundles()
    bundle = bundles[0] if bundles else {}
    spawn_request, _notes = spawn_from_bundle(bundle)
    routed = route_spawn_bundle(spawn_request, observed_at=FIXTURE_CLOCK)
    simulation = routed.get("simulation", {})
    wrapped = attach_translation_envelope_to_result(
        simulation if isinstance(simulation, dict) else routed,
        source_organ=SOURCE_ORGAN,
        claim_type="INHERITANCE_PACKET",
    )
    receipt = simulation.get("receipt") if isinstance(simulation, dict) else None
    if isinstance(receipt, dict):
        wrapped["lifecycle_receipt_envelope"] = emit_fixture_lifecycle_receipt(receipt)["translation_envelope"]
    spawn = record_spawn_request(spawn_request)
    spawn_wrapped = attach_translation_envelope_to_result(
        spawn, source_organ=SOURCE_ORGAN, claim_type="INHERITANCE_PACKET", receipt_key="spawn_request"
    )
    sample = emit_tep_wrapped_claim(
        source_organ=SOURCE_ORGAN,
        claim_type="INHERITANCE_PACKET",
        claim_id="claim:rib:inheritance-fixture",
        structured_value={"child_authority_created": False, "proposal_only": True},
    )
    return {
        "organ": SOURCE_ORGAN,
        "has_translation_envelope": "translation_envelope" in wrapped,
        "authority_created": False,
        "child_authority_created": False,
        "fixture_result": wrapped,
        "spawn_envelope": spawn_wrapped.get("translation_envelope"),
        "sample_emission": sample,
        "live_fenced": fence_live_rtc_emission()["status"] == "fenced",
    }


__all__ = [
    "SOURCE_ORGAN",
    "emit_fixture_lifecycle_receipt",
    "fence_live_rtc_emission",
    "run_rib_fixture_emission",
]
