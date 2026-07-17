"""MEM-LIVE evaluator — governed live memory mutation; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.mem_live.config import mem_refuse_authority_conversion
from hg_core.mem_live.errors import (
    MEM_AUTHORITY_CONVERSION_CONTAINED,
    MEM_COMMIT_FAKE_SINK,
    MEM_FAILED_CLOSED,
    MEM_RESTORE_RECORDED,
    MEM_WRITE_CANDIDATE_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    REFUSED_SECRET_LEAK,
)
from hg_core.mem_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_memory_mutation.adapter import commit_to_fake_sink, request_to_fake_sink
from hg_runtime.live_memory_mutation.fixtures import load_mem_fixtures
from hg_runtime.live_memory_mutation.rollback import restore_from_rollback, rollback_memory_mutation
from hg_runtime.live_memory_mutation.tep_emission import emit_fixture_write_candidate, run_mem_fixture_emission
from hg_runtime.live_memory_mutation.types import (
    FIXTURE_CLOCK,
    MemoryMutationReceipt,
    MemoryWriteCandidate,
    request_from_fixture,
)
from hg_runtime.live_memory_mutation.validator import validate_memory_mutation_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
}


def _candidate_id(request_id: str, mutation_kind: str) -> str:
    digest = canonical_hash({"request_id": request_id, "mutation_kind": mutation_kind})
    return f"mem-cand-{digest.rsplit(':', 1)[-1][:12]}"


def _receipt_id(request_id: str, candidate_id: str) -> str:
    digest = canonical_hash({"request_id": request_id, "candidate_id": candidate_id})
    return f"mem-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, MEM_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "durable_write_performed": False,
        "live_action_performed": False,
        "emitted_events": ("MEM_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_memory_mutation(
    request_data: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process request/commit path for memory mutation; fake-sink only."""
    clear_registry_cache()
    load_registry()
    request = request_from_fixture(request_data)
    validated = validate_memory_mutation_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        return {
            **validated,
            "request": request.to_payload(),
            "permission_granted": False,
            "durable_write_performed": False,
            "live_action_performed": False,
            "emitted_events": ("MEM_MUTATION_REFUSED",),
        }

    candidate = MemoryWriteCandidate(
        candidate_id=_candidate_id(request.request_id, request.mutation_kind),
        request_id=request.request_id,
        mutation_kind=request.mutation_kind,
        memory_key=request.memory_key,
        payload_digest=request.payload_digest,
        operator_ref=request.operator_ref,
        rollback_plan_ref=request.rollback_plan_ref,
    )
    staged = request_to_fake_sink(candidate, observed_at=observed_at)
    tep_wrapped = emit_fixture_write_candidate(candidate.to_payload())

    if request.mutation_kind == "restore":
        rollback_record = {
            "rollback_id": f"mem-rbk-restore-{request.request_id[-8:]}",
            "memory_key": request.memory_key,
        }
        restore_result = restore_from_rollback(
            rollback_record,
            restored_digest=request.payload_digest,
            observed_at=observed_at,
        )
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": MEM_RESTORE_RECORDED,
            "request": request.to_payload(),
            "candidate": candidate.to_payload(),
            "staged_sink": staged,
            "tep_wrapped": tep_wrapped,
            "restore_result": restore_result,
            "evidence_admissible": validated.get("evidence_admissible", False),
            "permission_granted": False,
            "durable_write_performed": False,
            "live_action_performed": False,
            "emitted_events": ("MEM_RESTORE_RECORDED",),
            "observed_at": observed_at,
        }

    receipt = MemoryMutationReceipt(
        receipt_id=_receipt_id(request.request_id, candidate.candidate_id),
        request_id=request.request_id,
        candidate_id=candidate.candidate_id,
        mutation_kind=request.mutation_kind,
        status="recorded",
        reason_code=MEM_WRITE_CANDIDATE_BOUND,
        operator_ref=request.operator_ref,
        evidence_admissible=bool(validated.get("evidence_admissible")),
        rollback_acknowledged=bool(request.rollback_plan_ref),
        restore_available=False,
    )
    committed = commit_to_fake_sink(receipt, observed_at=observed_at)

    rollback_result: dict[str, object] | None = None
    if request.rollback_plan_ref:
        rollback_result = rollback_memory_mutation(
            receipt,
            memory_key=request.memory_key,
            prior_digest=f"prior:{request.payload_digest}",
            observed_at=observed_at,
        )
        receipt = MemoryMutationReceipt(
            receipt_id=receipt.receipt_id,
            request_id=receipt.request_id,
            candidate_id=receipt.candidate_id,
            mutation_kind=receipt.mutation_kind,
            status="recorded",
            reason_code=MEM_COMMIT_FAKE_SINK,
            operator_ref=receipt.operator_ref,
            evidence_admissible=receipt.evidence_admissible,
            rollback_acknowledged=True,
            restore_available=True,
        )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": MEM_COMMIT_FAKE_SINK,
        "request": request.to_payload(),
        "candidate": candidate.to_payload(),
        "receipt": receipt.to_payload(),
        "staged_sink": staged,
        "committed_sink": committed,
        "tep_wrapped": tep_wrapped,
        "rollback_result": rollback_result,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "durable_write_performed": False,
        "live_action_performed": False,
        "emitted_events": ("MEM_WRITE_CANDIDATE_RECORDED", "MEM_FAKE_SINK_COMMITTED"),
        "observed_at": observed_at,
    }


def process_mem_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and mem_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["mutation_request"])
            except Exception:
                return {
                    **advisory_only_marker(),
                    "status": "refused",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_SECRET_LEAK,
                    "permission_granted": False,
                    "durable_write_performed": False,
                    "live_action_performed": False,
                    "emitted_events": ("MEM_FAILED_CLOSED",),
                }
        if adversarial in _ADVERSARIAL_REASON:
            if adversarial != "secret_leak":
                return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("mutation_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": MEM_FAILED_CLOSED,
            "permission_granted": False,
            "durable_write_performed": False,
            "live_action_performed": False,
            "emitted_events": ("MEM_FAILED_CLOSED",),
        }

    try:
        request = request_from_fixture(req_data)
    except Exception as exc:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": getattr(exc, "code", REFUSED_SECRET_LEAK),
            "permission_granted": False,
            "durable_write_performed": False,
            "live_action_performed": False,
            "emitted_events": ("MEM_FAILED_CLOSED",),
        }

    if adversarial == "authority_conversion" and request.treat_as_authority:
        return _contain_adversarial(bundle, signal="authority_conversion")

    result = process_memory_mutation(req_data, observed_at=observed_at)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_mem_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_mem_fixtures()
    results = [process_mem_bundle(b, observed_at=observed_at) for b in bundles]
    all_non_authority = all(r.get("permission_granted") is False for r in results)
    no_durable = all(r.get("durable_write_performed") is not True for r in results)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "mem.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all_non_authority,
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_durable_writes": no_durable,
        "observed_at": observed_at,
    }


def replay_fixture_stream(
    bundles: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for bundle in bundles:
        result = process_mem_bundle(bundle, observed_at=observed_at)
        results.append(result)
        receipt = result.get("receipt")
        candidate = result.get("candidate")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
        elif isinstance(candidate, dict):
            hashes.append(str(candidate.get("record_hash", "")))
        else:
            hashes.append(str(result.get("reason_code", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


def run_memory_mutation_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Runtime adapter entry — fixture request/commit with TEP emission."""
    valid_bundle = next(b for b in load_mem_fixtures() if b["bundle_id"] == "mem-valid-write")
    mutation = process_mem_bundle(valid_bundle, observed_at=observed_at)
    tep = run_mem_fixture_emission(mutation)
    rollback_bundle = next(b for b in load_mem_fixtures() if b["bundle_id"] == "mem-valid-rollback")
    rollback_path = process_mem_bundle(rollback_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "mem.advisory.mutation_adapter_fixture",
        "mutation_result": mutation,
        "rollback_result": rollback_path,
        "tep_emission": tep,
        "durable_write_performed": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = [
    "analyze_mem_fixtures",
    "process_mem_bundle",
    "process_memory_mutation",
    "replay_fixture_stream",
    "run_memory_mutation_fixture",
]
