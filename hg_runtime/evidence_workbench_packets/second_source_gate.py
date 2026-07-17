"""EWP-2 second-source requirement gate."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.independence_policy import evaluate_independence
from hg_runtime.evidence_workbench_packets.second_source import (
    build_packet_second_source_requirement,
    build_packet_second_source_result,
)


def build_second_source_fixtures() -> list[dict]:
    """Deterministic claim packet scenarios exercising every second-source outcome."""
    return [
        {
            "packet_id": "ewp2-packet-not-required",
            "claim_id": "ewp2-claim-not-required",
            "source_ids": ["ewp2-source-a"],
            "second_source_required": False,
        },
        {
            "packet_id": "ewp2-packet-missing",
            "claim_id": "ewp2-claim-missing",
            "source_ids": ["ewp2-source-a"],
            "second_source_required": True,
        },
        {
            "packet_id": "ewp2-packet-duplicate",
            "claim_id": "ewp2-claim-duplicate",
            "source_ids": ["ewp2-source-a", "ewp2-source-a-copy"],
            "duplicate_primary": {"ewp2-source-a-copy": "ewp2-source-a"},
            "second_source_required": True,
        },
        {
            "packet_id": "ewp2-packet-not-independent",
            "claim_id": "ewp2-claim-not-independent",
            "source_ids": ["ewp2-source-a", "ewp2-source-a-copy", "ewp2-source-b-copy"],
            "duplicate_primary": {"ewp2-source-a-copy": "ewp2-source-a", "ewp2-source-b-copy": "ewp2-source-b"},
            "second_source_required": True,
        },
        {
            "packet_id": "ewp2-packet-review-ready",
            "claim_id": "ewp2-claim-review-ready",
            "source_ids": ["ewp2-source-a", "ewp2-source-b"],
            "second_source_required": True,
        },
        {
            "packet_id": "ewp2-packet-conflict",
            "claim_id": "ewp2-claim-conflict",
            "source_ids": ["ewp2-source-a", "ewp2-source-b"],
            "conflict_source_ids": {"ewp2-source-a"},
            "second_source_required": True,
        },
        {
            "packet_id": "ewp2-packet-quarantine",
            "claim_id": "ewp2-claim-quarantine",
            "source_ids": ["ewp2-source-a", "ewp2-source-b"],
            "quarantine_source_ids": {"ewp2-source-b"},
            "second_source_required": True,
        },
        {
            "packet_id": "ewp2-packet-fever",
            "claim_id": "ewp2-claim-fever",
            "source_ids": ["ewp2-source-a", "ewp2-source-b"],
            "fever_source_ids": {"ewp2-source-a"},
            "second_source_required": True,
        },
        {
            "packet_id": "ewp2-packet-redaction",
            "claim_id": "ewp2-claim-redaction",
            "source_ids": ["ewp2-source-a", "ewp2-source-b"],
            "redaction_blocked_source_ids": {"ewp2-source-b"},
            "second_source_required": True,
        },
    ]


def build_second_source_gate_layer(scenarios: list[dict] | None = None) -> dict:
    scenarios = scenarios or build_second_source_fixtures()
    requirements: list[dict] = []
    results: list[dict] = []

    for idx, scenario in enumerate(scenarios, start=1):
        req = build_packet_second_source_requirement(
            requirement_id=f"ewp2-req-{idx:03d}",
            packet_id=scenario["packet_id"],
            claim_id=scenario["claim_id"],
            second_source_required=scenario["second_source_required"],
        )
        outcome, independent_count = evaluate_independence(
            source_ids=scenario["source_ids"],
            duplicate_primary=scenario.get("duplicate_primary", {}),
            conflict_source_ids=scenario.get("conflict_source_ids", set()),
            quarantine_source_ids=scenario.get("quarantine_source_ids", set()),
            fever_source_ids=scenario.get("fever_source_ids", set()),
            redaction_blocked_source_ids=scenario.get("redaction_blocked_source_ids", set()),
            second_source_required=scenario["second_source_required"],
        )
        result = build_packet_second_source_result(
            result_id=f"ewp2-result-{idx:03d}",
            requirement_id=req["requirement_id"],
            packet_id=scenario["packet_id"],
            outcome=outcome,
            independent_source_count=independent_count,
        )
        requirements.append(req)
        results.append(result)

    return {
        "packet_second_source_requirements": requirements,
        "packet_second_source_results": results,
    }
