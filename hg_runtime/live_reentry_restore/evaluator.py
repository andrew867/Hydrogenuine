"""REB-RESTORE-LIVE evaluator — governed live reentry restore; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.policy_safety.hashing import canonical_hash
from hg_core.reb_restore_live.config import reb_restore_refuse_authority_conversion
from hg_core.reb_restore_live.errors import (
    REB_RESTORE_AUTHORITY_CONVERSION_CONTAINED, REB_RESTORE_COMMIT_FAKE_SINK, REB_RESTORE_FAILED_CLOSED,
    REB_RESTORE_CANDIDATE_BOUND, REFUSED_AUTHORITY_CONVERSION, REFUSED_OUT_OF_SCOPE_LIVE_ACTION, REFUSED_SECRET_LEAK,
)
from hg_core.reb_restore_live.no_authority import advisory_only_marker
from hg_runtime.live_reentry_restore.adapter import commit_to_fake_sink, stage_to_fake_sink
from hg_runtime.live_reentry_restore.fixtures import load_reb_restore_fixtures
from hg_runtime.live_reentry_restore.rollback import compensation_record, continuity_refusal_record
from hg_runtime.live_reentry_restore.tep_emission import emit_fixture_restore_candidate, run_reb_restore_fixture_emission
from hg_runtime.live_reentry_restore.types import FIXTURE_CLOCK, RestoreCandidate, RestoreReceipt, request_from_fixture
from hg_runtime.live_reentry_restore.validator import validate_checkpoint_restore_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
}


def _candidate_id(request_id: str, restore_kind: str) -> str:
    digest = canonical_hash({"request_id": request_id, "restore_kind": restore_kind})
    return f"reb-cand-{digest.rsplit(':', 1)[-1][:12]}"


def _receipt_id(request_id: str, candidate_id: str) -> str:
    digest = canonical_hash({"request_id": request_id, "candidate_id": candidate_id})
    return f"reb-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(), "status": "contained", "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, REB_RESTORE_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal, "permission_granted": False, "live_restore_performed": False,
        "live_action_performed": False, "emitted_events": ("REB_RESTORE_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_checkpoint_restore(request_data: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    clear_registry_cache()
    load_registry()
    request = request_from_fixture(request_data)
    validated = validate_checkpoint_restore_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        return {**validated, "request": request.to_payload(), "permission_granted": False,
                "live_restore_performed": False, "live_action_performed": False,
                "emitted_events": ("REB_RESTORE_REFUSED",)}

    candidate = RestoreCandidate(
        candidate_id=_candidate_id(request.request_id, request.restore_kind),
        request_id=request.request_id, restore_kind=request.restore_kind,
        checkpoint_digest=request.checkpoint_digest, continuity_claim_ref=request.continuity_claim_ref,
        operator_ref=request.operator_ref,
    )
    staged = stage_to_fake_sink(candidate, observed_at=observed_at)
    tep_wrapped = emit_fixture_restore_candidate(candidate.to_payload())
    receipt = RestoreReceipt(
        receipt_id=_receipt_id(request.request_id, candidate.candidate_id),
        request_id=request.request_id, candidate_id=candidate.candidate_id,
        restore_kind=request.restore_kind, status="recorded", reason_code=REB_RESTORE_CANDIDATE_BOUND,
        operator_ref=request.operator_ref, evidence_admissible=bool(validated.get("evidence_admissible")),
    )
    committed = commit_to_fake_sink(receipt, observed_at=observed_at)

    continuity_refusal_result: dict[str, object] | None = None
    compensation_result: dict[str, object] | None = None
    if request_data.get("continuity_refusal_path") or request.request_id.endswith("continuity-refusal"):
        claim_ref = str(request.continuity_claim_ref or "continuity:refusal:fixture")
        continuity_refusal_result = continuity_refusal_record(receipt, continuity_claim_ref=claim_ref, observed_at=observed_at)
        c_record = continuity_refusal_result.get("continuity_refusal_record")
        if isinstance(c_record, dict):
            compensation_result = compensation_record(c_record, observed_at=observed_at)
        receipt = RestoreReceipt(
            receipt_id=receipt.receipt_id, request_id=receipt.request_id, candidate_id=receipt.candidate_id,
            restore_kind=receipt.restore_kind, status="recorded", reason_code=REB_RESTORE_COMMIT_FAKE_SINK,
            operator_ref=receipt.operator_ref, evidence_admissible=receipt.evidence_admissible,
        )

    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": REB_RESTORE_COMMIT_FAKE_SINK,
        "request": request.to_payload(), "candidate": candidate.to_payload(), "receipt": receipt.to_payload(),
        "staged_sink": staged, "committed_sink": committed, "tep_wrapped": tep_wrapped,
        "continuity_refusal_result": continuity_refusal_result, "compensation_result": compensation_result,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False, "authority_created": False, "live_restore_performed": False,
        "live_action_performed": False,
        "emitted_events": ("REB_RESTORE_CANDIDATE_RECORDED", "REB_RESTORE_FAKE_SINK_COMMITTED"),
        "observed_at": observed_at,
    }


def process_reb_restore_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and reb_restore_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["restore_request"])
            except Exception:
                return {**advisory_only_marker(), "status": "refused", "bundle_id": bundle.get("bundle_id"),
                        "reason_code": REFUSED_SECRET_LEAK, "permission_granted": False,
                        "live_restore_performed": False, "emitted_events": ("REB_RESTORE_FAILED_CLOSED",)}
        if adversarial in _ADVERSARIAL_REASON and adversarial != "secret_leak":
            return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("restore_request")
    if not req_data:
        return {**advisory_only_marker(), "status": "fail_closed", "bundle_id": bundle.get("bundle_id"),
                "reason_code": REB_RESTORE_FAILED_CLOSED, "permission_granted": False,
                "live_restore_performed": False, "emitted_events": ("REB_RESTORE_FAILED_CLOSED",)}

    try:
        request = request_from_fixture(req_data)
    except Exception as exc:
        return {**advisory_only_marker(), "status": "refused", "bundle_id": bundle.get("bundle_id"),
                "reason_code": getattr(exc, "code", REFUSED_SECRET_LEAK), "permission_granted": False,
                "live_restore_performed": False, "emitted_events": ("REB_RESTORE_FAILED_CLOSED",)}

    if adversarial == "authority_conversion" and request.treat_as_authority:
        return _contain_adversarial(bundle, signal="authority_conversion")

    if bundle.get("bundle_id") == "reb-restore-valid-continuity-refusal":
        req_data = {**req_data, "continuity_refusal_path": True}

    result = process_checkpoint_restore(req_data, observed_at=observed_at)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_reb_restore_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_reb_restore_fixtures()
    results = [process_reb_restore_bundle(b, observed_at=observed_at) for b in bundles]
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": "reb_restore.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles), "results": results,
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_live_restore": all(r.get("live_restore_performed") is not True for r in results),
        "observed_at": observed_at,
    }


def replay_fixture_stream(bundles: list[dict[str, Any]], *, observed_at: str = FIXTURE_CLOCK) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for bundle in bundles:
        result = process_reb_restore_bundle(bundle, observed_at=observed_at)
        results.append(result)
        receipt = result.get("receipt")
        candidate = result.get("candidate")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
        elif isinstance(candidate, dict):
            hashes.append(str(candidate.get("record_hash", "")))
        else:
            hashes.append(str(result.get("reason_code", "")))
    return results, canonical_hash({"replay": "|".join(hashes)})


def run_reentry_restore_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    valid_bundle = next(b for b in load_reb_restore_fixtures() if b["bundle_id"] == "reb-restore-valid-restore")
    restore = process_reb_restore_bundle(valid_bundle, observed_at=observed_at)
    tep = run_reb_restore_fixture_emission(restore)
    refusal_bundle = next(b for b in load_reb_restore_fixtures() if b["bundle_id"] == "reb-restore-valid-continuity-refusal")
    refusal_path = process_reb_restore_bundle(refusal_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": "reb_restore.advisory.restore_adapter_fixture",
        "restore_result": restore, "continuity_refusal_result": refusal_path, "tep_emission": tep,
        "live_restore_performed": False, "live_action_performed": False, "permission_granted": False, "observed_at": observed_at,
    }


__all__ = [
    "analyze_reb_restore_fixtures", "process_checkpoint_restore", "process_reb_restore_bundle",
    "replay_fixture_stream", "run_reentry_restore_fixture",
]
