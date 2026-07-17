"""A0-HM evaluator — root posture pipeline, fixture-only."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.a0_hm_cluster.no_authority import advisory_only_marker
from hg_runtime.agent_zero_heart_mind.fixtures import load_fixture_bundles
from hg_runtime.agent_zero_heart_mind.receipt import emit_non_fusion_receipt
from hg_runtime.agent_zero_heart_mind.reception import apply_reception
from hg_runtime.agent_zero_heart_mind.router import route_signal
from hg_runtime.agent_zero_heart_mind.snapshot import create_posture_snapshot
from hg_runtime.agent_zero_heart_mind.types import FIXTURE_CLOCK, HeartMindSignal, signal_from_fixture


def process_heart_mind_signal(
    signal: HeartMindSignal,
    *,
    treat_as_authority: bool = False,
    treat_as_permission: bool = False,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    if treat_as_permission:
        from hg_runtime.agent_zero_heart_mind.policies import validate_signal_not_permission

        validate_signal_not_permission(signal, treat_as_permission=True)

    received = apply_reception(signal, treat_as_authority=treat_as_authority)
    routed = route_signal(signal, received)
    reception_payload = received.get("reception")
    route_payload = routed.get("route_decision")
    assert isinstance(reception_payload, dict)
    assert isinstance(route_payload, dict)

    events = tuple(
        list(received.get("emitted_events", ()))
        + list(routed.get("emitted_events", ()))
    )
    receipt = emit_non_fusion_receipt(
        signal,
        reception_ref=str(reception_payload["reception_id"]),
        route_decision_ref=str(route_payload["route_decision_id"]),
        emitted_events=events,
    )
    snapshot = create_posture_snapshot(
        active_signal_refs=(f"a0hm:{signal.signal_id}",),
        active_route_refs=tuple(routed.get("route_targets", ())),  # type: ignore[arg-type]
        active_boundary_refs=tuple(routed.get("route_targets", ())),  # type: ignore[arg-type]
        unresolved_signal_refs=()
        if received.get("status") != "contained"
        else (f"a0hm:{signal.signal_id}",),
        observed_at=observed_at,
    )

    status = routed.get("status", "routed")
    if received.get("status") == "contained":
        status = "contained"

    return {
        **advisory_only_marker(),
        "status": status,
        "signal_id": signal.signal_id,
        "source_type": signal.source_type,
        "reception": reception_payload,
        "route_decision": route_payload,
        "non_fusion_receipt": receipt.get("non_fusion_receipt"),
        "posture_snapshot": snapshot.get("posture_snapshot"),
        "permission_granted": False,
        "route_targets": routed.get("route_targets"),
    }


def process_fixture_dict(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return process_heart_mind_signal(signal_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def analyze_fixture_bundles() -> dict[str, Any]:
    results: list[dict[str, object]] = []
    for bundle in load_fixture_bundles():
        signal = bundle["signal"]
        assert isinstance(signal, HeartMindSignal)
        results.append(process_heart_mind_signal(signal))
    all_advisory = all(r.get("permission_granted") is False for r in results)
    return {
        "fixture_analysis_only": True,
        "bundle_count": len(results),
        "all_advisory": all_advisory,
        "results": results,
    }


def replay_fixture_stream(fixtures: list[dict[str, str]]) -> str:
    digests: list[str] = []
    for fixture in fixtures:
        result = process_fixture_dict(fixture)
        digests.append(
            canonical_hash(
                {
                    "signal_id": result.get("signal_id"),
                    "status": result.get("status"),
                    "route_targets": result.get("route_targets"),
                }
            )
        )
    return canonical_hash({"digests": digests})


__all__ = [
    "analyze_fixture_bundles",
    "process_fixture_dict",
    "process_heart_mind_signal",
    "replay_fixture_stream",
]
