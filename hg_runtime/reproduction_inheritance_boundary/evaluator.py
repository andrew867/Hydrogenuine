"""RIB evaluator — reproduction/inheritance is not permission."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.rib_cluster.errors import (
    REFUSED_BOOTSTRAP_AS_PERMISSION,
    REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD,
    REFUSED_PARTIAL_SPAWN_WITHOUT_ROLLBACK,
    REFUSED_UNBOUNDED_RETRY,
    RIB_CHILD_FAILED_SPAWN_RECORDED,
    RIB_CHILD_LIFECYCLE_RECEIPT_CREATED,
    RIB_CHILD_PARTIAL_SPAWN_RECORDED,
    RIB_CHILD_ROLLBACK_REQUESTED,
    RIB_CHILD_SPAWN_DENIED,
    RIB_PARENT_CHILD_AUTHORITY_SEPARATED,
    RIB_SPAWN_REQUEST_RECORDED,
    RibValidationError,
)
from hg_core.rib_cluster.no_authority import advisory_only_marker
from hg_runtime.reproduction_inheritance_boundary.events import (
    inheritance_selection_event,
    lifecycle_selection_event,
)
from hg_runtime.reproduction_inheritance_boundary.fixtures import load_fixture_bundles, spawn_from_bundle
from hg_runtime.reproduction_inheritance_boundary.queue import FakeChildBootstrapQueue
from hg_runtime.reproduction_inheritance_boundary.router import (
    refuse_rib_as_authority,
    route_spawn_request,
)
from hg_runtime.reproduction_inheritance_boundary.types import (
    FIXTURE_CLOCK,
    ChildLifecycleReceipt,
    FailedSpawnRecord,
    SpawnRequest,
    spawn_request_from_fixture,
)

_MAX_RETRY_ATTEMPTS = 1


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def record_spawn_request(
    spawn_request: SpawnRequest,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_rib_as_authority(treat_as_authority=True)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": RIB_SPAWN_REQUEST_RECORDED,
        "spawn_request": spawn_request.to_payload(),
        "permission_granted": False,
        "child_authority_created": False,
        "emitted_events": ("RIB_SPAWN_REQUEST_RECORDED",),
    }


def simulate_spawn_outcome(
    routed: dict[str, object],
    *,
    outcome: str,
    failure_type: str | None = None,
    partial_artifact_refs: tuple[str, ...] = (),
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    if routed.get("status") == "contained":
        spawn_payload = routed.get("spawn_request")
        spawn_id = "unknown"
        if isinstance(spawn_payload, dict):
            spawn_id = str(spawn_payload.get("spawn_request_id", "unknown"))
        receipt = ChildLifecycleReceipt(
            receipt_id=_deterministic_id("rib-receipt", "denied-contained"),
            spawn_request_ref=f"rib:{spawn_id}",
            lifecycle_state="denied",
            state_reason=str(routed.get("reason_code", "contained")),
            evidence_refs=("ev:contained",),
            rollback_refs=(),
            created_at=observed_at,
        )
        ChildLifecycleReceipt.validate_negative_proofs(receipt.to_payload())
        return {
            **advisory_only_marker(),
            "status": "denied",
            "reason_code": RIB_CHILD_SPAWN_DENIED,
            "receipt": receipt.to_payload(),
            "child_authority_created": False,
            "emitted_events": ("RIB_CHILD_SPAWN_DENIED", "RIB_CHILD_LIFECYCLE_RECEIPT_CREATED"),
        }

    spawn_payload = routed.get("spawn_request")
    if not isinstance(spawn_payload, dict):
        raise RibValidationError("rib.validation.spawn_payload", "missing spawn_request payload")
    spawn_ref = f"rib:{spawn_payload['spawn_request_id']}"
    bootstrap_payload = routed.get("bootstrap_packet")
    bootstrap_ref = None
    if isinstance(bootstrap_payload, dict):
        bootstrap_ref = f"rib:{bootstrap_payload['bootstrap_packet_id']}"

    decisions = routed.get("inheritance_decisions", [])
    if isinstance(decisions, list):
        for row in decisions:
            if not isinstance(row, dict):
                continue
            if row.get("decision") == "forbidden":
                receipt = ChildLifecycleReceipt(
                    receipt_id=_deterministic_id("rib-receipt", spawn_ref, "forbidden"),
                    spawn_request_ref=spawn_ref,
                    lifecycle_state="denied",
                    state_reason=str(row.get("reason", "forbidden inheritance")),
                    evidence_refs=(str(row.get("candidate_ref", "unknown")),),
                    rollback_refs=(),
                    created_at=observed_at,
                    bootstrap_packet_ref=bootstrap_ref,
                )
                ChildLifecycleReceipt.validate_negative_proofs(receipt.to_payload())
                event = inheritance_selection_event(
                    str(row.get("decision", "")),
                    str(row.get("inheritance_type", "")),
                )
                return {
                    **advisory_only_marker(),
                    "status": "denied",
                    "reason_code": RIB_CHILD_SPAWN_DENIED,
                    "receipt": receipt.to_payload(),
                    "child_authority_created": False,
                    "emitted_events": tuple(
                        e
                        for e in (
                            "RIB_INHERITANCE_DECISION_RECORDED",
                            event,
                            "RIB_CHILD_SPAWN_DENIED",
                            "RIB_CHILD_LIFECYCLE_RECEIPT_CREATED",
                        )
                        if e
                    ),
                }

    if outcome == "failed_spawn":
        failed = FailedSpawnRecord(
            failed_spawn_id=_deterministic_id("rib-failed", spawn_ref),
            spawn_request_ref=spawn_ref,
            failure_type=failure_type or "child_init_failed",  # type: ignore[arg-type]
            partial_artifact_refs=partial_artifact_refs,
            cleanup_required=bool(partial_artifact_refs),
            cleanup_refs=("rib:cleanup-default",) if partial_artifact_refs else (),
            retry_policy="retry_after_operator_review",
            evidence_refs=("ev:failed-spawn",),
            bootstrap_packet_ref=bootstrap_ref,
        )
        receipt = ChildLifecycleReceipt(
            receipt_id=_deterministic_id("rib-receipt", spawn_ref, "failed"),
            spawn_request_ref=spawn_ref,
            lifecycle_state="failed_spawn",
            state_reason=RIB_CHILD_FAILED_SPAWN_RECORDED,
            evidence_refs=("ev:failed-spawn",),
            rollback_refs=(),
            created_at=observed_at,
            bootstrap_packet_ref=bootstrap_ref,
        )
        ChildLifecycleReceipt.validate_negative_proofs(receipt.to_payload())
        return {
            **advisory_only_marker(),
            "status": "failed_spawn",
            "reason_code": RIB_CHILD_FAILED_SPAWN_RECORDED,
            "failed_spawn": failed.to_payload(),
            "receipt": receipt.to_payload(),
            "child_authority_created": False,
            "emitted_events": (
                "RIB_CHILD_FAILED_SPAWN_RECORDED",
                "RIB_CHILD_LIFECYCLE_RECEIPT_CREATED",
                "RIB_PARENT_CHILD_AUTHORITY_SEPARATED",
            ),
        }

    if outcome == "partial_spawn":
        if not partial_artifact_refs:
            raise RibValidationError(
                REFUSED_PARTIAL_SPAWN_WITHOUT_ROLLBACK,
                "partial spawn requires artifact refs and rollback",
            )
        failed = FailedSpawnRecord(
            failed_spawn_id=_deterministic_id("rib-failed", spawn_ref, "partial"),
            spawn_request_ref=spawn_ref,
            failure_type="partial_state_created",
            partial_artifact_refs=partial_artifact_refs,
            cleanup_required=True,
            cleanup_refs=("rib:rollback-default",),
            retry_policy="no_retry",
            evidence_refs=tuple(partial_artifact_refs),
            bootstrap_packet_ref=bootstrap_ref,
        )
        receipt = ChildLifecycleReceipt(
            receipt_id=_deterministic_id("rib-receipt", spawn_ref, "partial"),
            spawn_request_ref=spawn_ref,
            lifecycle_state="partial_spawn",
            state_reason=RIB_CHILD_PARTIAL_SPAWN_RECORDED,
            evidence_refs=tuple(partial_artifact_refs),
            rollback_refs=("rib:rollback-default",),
            created_at=observed_at,
            bootstrap_packet_ref=bootstrap_ref,
        )
        ChildLifecycleReceipt.validate_negative_proofs(receipt.to_payload())
        return {
            **advisory_only_marker(),
            "status": "partial_spawn",
            "reason_code": RIB_CHILD_PARTIAL_SPAWN_RECORDED,
            "failed_spawn": failed.to_payload(),
            "receipt": receipt.to_payload(),
            "child_authority_created": False,
            "rollback_requested": True,
            "emitted_events": (
                "RIB_CHILD_PARTIAL_SPAWN_RECORDED",
                "RIB_CHILD_ROLLBACK_REQUESTED",
                "RIB_CHILD_LIFECYCLE_RECEIPT_CREATED",
            ),
        }

    if outcome == "denied":
        receipt = ChildLifecycleReceipt(
            receipt_id=_deterministic_id("rib-receipt", spawn_ref, "denied"),
            spawn_request_ref=spawn_ref,
            lifecycle_state="denied",
            state_reason=RIB_CHILD_SPAWN_DENIED,
            evidence_refs=("ev:denied",),
            rollback_refs=(),
            created_at=observed_at,
            bootstrap_packet_ref=bootstrap_ref,
        )
        ChildLifecycleReceipt.validate_negative_proofs(receipt.to_payload())
        return {
            **advisory_only_marker(),
            "status": "denied",
            "reason_code": RIB_CHILD_SPAWN_DENIED,
            "receipt": receipt.to_payload(),
            "child_authority_created": False,
            "emitted_events": ("RIB_CHILD_SPAWN_DENIED", "RIB_CHILD_LIFECYCLE_RECEIPT_CREATED"),
        }

    receipt = ChildLifecycleReceipt(
        receipt_id=_deterministic_id("rib-receipt", spawn_ref, "bootstrap"),
        spawn_request_ref=spawn_ref,
        lifecycle_state="bootstrap_created",
        state_reason="fixture bootstrap packet only — no live spawn",
        evidence_refs=("ev:bootstrap-only",),
        rollback_refs=(),
        created_at=observed_at,
        bootstrap_packet_ref=bootstrap_ref,
    )
    ChildLifecycleReceipt.validate_negative_proofs(receipt.to_payload())
    return {
        **advisory_only_marker(),
        "status": "bootstrap_created",
        "reason_code": RIB_CHILD_LIFECYCLE_RECEIPT_CREATED,
        "receipt": receipt.to_payload(),
        "child_authority_created": False,
        "emitted_events": (
            "RIB_CHILD_BOOTSTRAP_PACKET_CREATED",
            "RIB_CHILD_LIFECYCLE_RECEIPT_CREATED",
            "RIB_PARENT_CHILD_AUTHORITY_SEPARATED",
        ),
    }


def route_spawn_bundle(
    spawn_request: SpawnRequest,
    *,
    notes: str = "",
    outcome: str = "bootstrap_only",
    failure_type: str | None = None,
    partial_artifact_refs: tuple[str, ...] = (),
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    recorded = record_spawn_request(spawn_request)
    routed = route_spawn_request(spawn_request, notes=notes, observed_at=observed_at)
    simulated = simulate_spawn_outcome(
        routed,
        outcome=outcome,
        failure_type=failure_type,
        partial_artifact_refs=partial_artifact_refs,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": simulated.get("status"),
        "recorded_spawn": recorded,
        "route": routed,
        "simulation": simulated,
        "permission_granted": False,
        "child_authority_created": False,
        "reproduction_is_advisory_only": True,
    }


def analyze_fixture_bundles(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    active = bundles if bundles is not None else load_fixture_bundles()
    results: list[dict[str, object]] = []
    for bundle in active:
        spawn_request, notes = spawn_from_bundle(bundle)
        outcome = str(bundle.get("spawn_outcome", "bootstrap_only"))
        partial_refs = tuple(bundle.get("partial_artifact_refs", ()))
        results.append(
            {
                "bundle_id": bundle.get("bundle_id"),
                "result": route_spawn_bundle(
                    spawn_request,
                    notes=notes,
                    outcome=outcome,
                    failure_type=bundle.get("failure_type"),
                    partial_artifact_refs=partial_refs,
                    observed_at=observed_at,
                ),
            }
        )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rib.advisory.fixture_bundles_analyzed",
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(
            r["result"].get("child_authority_created") is False  # type: ignore[index]
            for r in results
        ),
        "permission_granted": False,
    }


def replay_fixture_stream(
    fixtures: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for row in fixtures:
        spawn_request = spawn_request_from_fixture(row["spawn_request"])
        notes = str(row.get("notes", ""))
        outcome = str(row.get("spawn_outcome", "bootstrap_only"))
        result = route_spawn_bundle(
            spawn_request,
            notes=notes,
            outcome=outcome,
            failure_type=row.get("failure_type"),
            partial_artifact_refs=tuple(row.get("partial_artifact_refs", ())),
            observed_at=observed_at,
        )
        results.append(result)
        receipt = result.get("simulation", {})
        if isinstance(receipt, dict):
            inner = receipt.get("receipt")
            if isinstance(inner, dict):
                hashes.append(str(inner.get("record_hash", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def refuse_bootstrap_as_permission(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise RibValidationError(REFUSED_BOOTSTRAP_AS_PERMISSION, "bootstrap packet is not permission")


def refuse_failed_spawn_as_active_child(*, lifecycle_state: str) -> None:
    if lifecycle_state in {"failed_spawn", "partial_spawn", "denied"}:
        raise RibValidationError(
            REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD,
            "failed or partial spawn is not an active child",
        )


def refuse_unbounded_retry(*, attempt: int) -> None:
    if attempt > _MAX_RETRY_ATTEMPTS:
        raise RibValidationError(REFUSED_UNBOUNDED_RETRY, "spawn retry is bounded")


def enqueue_fixture_bootstrap_queue(
    bundles: tuple[dict[str, Any], ...] | None = None,
) -> dict[str, object]:
    queue = FakeChildBootstrapQueue()
    active = bundles if bundles is not None else load_fixture_bundles()
    enqueued: list[dict[str, object]] = []
    for bundle in active[:3]:
        spawn_request, _ = spawn_from_bundle(bundle)
        enqueued.append(queue.enqueue(spawn_request))
    return {
        **advisory_only_marker(),
        "status": "queued",
        "fake_queue_only": True,
        "queue_depth": queue.depth,
        "enqueued": enqueued,
        "permission_granted": False,
        "child_authority_created": False,
    }


__all__ = [
    "analyze_fixture_bundles",
    "enqueue_fixture_bootstrap_queue",
    "record_spawn_request",
    "refuse_bootstrap_as_permission",
    "refuse_failed_spawn_as_active_child",
    "refuse_unbounded_retry",
    "replay_fixture_stream",
    "route_spawn_bundle",
    "simulate_spawn_outcome",
]
