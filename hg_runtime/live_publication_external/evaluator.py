"""PUB-EXT-LIVE evaluator — governed live publication; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.policy_safety.hashing import canonical_hash
from hg_core.pub_ext_live.config import pub_ext_refuse_authority_conversion
from hg_core.pub_ext_live.errors import (
    PUB_EXT_AUTHORITY_CONVERSION_CONTAINED, PUB_EXT_COMMIT_FAKE_SINK, PUB_EXT_FAILED_CLOSED,
    PUB_EXT_RELEASE_CANDIDATE_BOUND, REFUSED_AUTHORITY_CONVERSION, REFUSED_OUT_OF_SCOPE_LIVE_ACTION, REFUSED_SECRET_LEAK,
)
from hg_core.pub_ext_live.no_authority import advisory_only_marker
from hg_runtime.live_publication_external.adapter import commit_to_fake_sink, stage_to_fake_sink
from hg_runtime.live_publication_external.fixtures import load_pub_ext_fixtures
from hg_runtime.live_publication_external.rollback import compensation_record, withdrawal_record
from hg_runtime.live_publication_external.tep_emission import emit_fixture_release_candidate, run_pub_ext_fixture_emission
from hg_runtime.live_publication_external.types import FIXTURE_CLOCK, PublicationCandidate, PublicationReceipt, request_from_fixture
from hg_runtime.live_publication_external.validator import validate_publication_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
}


def _candidate_id(request_id: str, release_kind: str) -> str:
    digest = canonical_hash({"request_id": request_id, "release_kind": release_kind})
    return f"pub-cand-{digest.rsplit(':', 1)[-1][:12]}"


def _receipt_id(request_id: str, candidate_id: str) -> str:
    digest = canonical_hash({"request_id": request_id, "candidate_id": candidate_id})
    return f"pub-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(), "status": "contained", "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, PUB_EXT_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal, "permission_granted": False, "published": False,
        "live_external_action": False, "live_action_performed": False,
        "emitted_events": ("PUB_EXT_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_publication_release(request_data: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    clear_registry_cache()
    load_registry()
    request = request_from_fixture(request_data)
    validated = validate_publication_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        return {**validated, "request": request.to_payload(), "permission_granted": False,
                "published": False, "live_external_action": False, "live_action_performed": False,
                "emitted_events": ("PUB_EXT_RELEASE_REFUSED",)}

    candidate = PublicationCandidate(
        candidate_id=_candidate_id(request.request_id, request.release_kind),
        request_id=request.request_id, release_kind=request.release_kind,
        content_digest=request.content_digest, disclosure_tier="tier:fixture",
        operator_ref=request.operator_ref, rollback_plan_ref=request.rollback_plan_ref,
    )
    staged = stage_to_fake_sink(candidate, observed_at=observed_at)
    tep_wrapped = emit_fixture_release_candidate(candidate.to_payload())
    receipt = PublicationReceipt(
        receipt_id=_receipt_id(request.request_id, candidate.candidate_id),
        request_id=request.request_id, candidate_id=candidate.candidate_id,
        release_kind=request.release_kind, status="recorded", reason_code=PUB_EXT_RELEASE_CANDIDATE_BOUND,
        operator_ref=request.operator_ref, evidence_admissible=bool(validated.get("evidence_admissible")),
    )
    committed = commit_to_fake_sink(receipt, observed_at=observed_at)

    withdrawal_result: dict[str, object] | None = None
    compensation_result: dict[str, object] | None = None
    if request_data.get("withdrawal_path") or request.request_id.endswith("withdrawal"):
        withdrawal_result = withdrawal_record(receipt, content_digest=request.content_digest, observed_at=observed_at)
        w_record = withdrawal_result.get("withdrawal_record")
        if isinstance(w_record, dict):
            compensation_result = compensation_record(w_record, observed_at=observed_at)
        receipt = PublicationReceipt(
            receipt_id=receipt.receipt_id, request_id=receipt.request_id, candidate_id=receipt.candidate_id,
            release_kind=receipt.release_kind, status="recorded", reason_code=PUB_EXT_COMMIT_FAKE_SINK,
            operator_ref=receipt.operator_ref, evidence_admissible=receipt.evidence_admissible,
        )

    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": PUB_EXT_COMMIT_FAKE_SINK,
        "request": request.to_payload(), "candidate": candidate.to_payload(), "receipt": receipt.to_payload(),
        "staged_sink": staged, "committed_sink": committed, "tep_wrapped": tep_wrapped,
        "withdrawal_result": withdrawal_result, "compensation_result": compensation_result,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False, "authority_created": False, "published": False,
        "live_external_action": False, "live_action_performed": False,
        "emitted_events": ("PUB_EXT_RELEASE_CANDIDATE_RECORDED", "PUB_EXT_FAKE_SINK_COMMITTED"),
        "observed_at": observed_at,
    }


def process_pub_ext_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and pub_ext_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["release_request"])
            except Exception:
                return {**advisory_only_marker(), "status": "refused", "bundle_id": bundle.get("bundle_id"),
                        "reason_code": REFUSED_SECRET_LEAK, "permission_granted": False, "published": False,
                        "live_external_action": False, "emitted_events": ("PUB_EXT_FAILED_CLOSED",)}
        if adversarial in _ADVERSARIAL_REASON and adversarial != "secret_leak":
            return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("release_request")
    if not req_data:
        return {**advisory_only_marker(), "status": "fail_closed", "bundle_id": bundle.get("bundle_id"),
                "reason_code": PUB_EXT_FAILED_CLOSED, "permission_granted": False, "published": False,
                "live_external_action": False, "emitted_events": ("PUB_EXT_FAILED_CLOSED",)}

    try:
        request = request_from_fixture(req_data)
    except Exception as exc:
        return {**advisory_only_marker(), "status": "refused", "bundle_id": bundle.get("bundle_id"),
                "reason_code": getattr(exc, "code", REFUSED_SECRET_LEAK), "permission_granted": False,
                "published": False, "live_external_action": False, "emitted_events": ("PUB_EXT_FAILED_CLOSED",)}

    if adversarial == "authority_conversion" and request.treat_as_authority:
        return _contain_adversarial(bundle, signal="authority_conversion")

    if bundle.get("bundle_id") == "pub-ext-valid-withdrawal":
        req_data = {**req_data, "withdrawal_path": True}

    result = process_publication_release(req_data, observed_at=observed_at)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_pub_ext_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_pub_ext_fixtures()
    results = [process_pub_ext_bundle(b, observed_at=observed_at) for b in bundles]
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": "pub_ext.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles), "results": results,
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_live_external_action": all(r.get("live_external_action") is not True for r in results),
        "observed_at": observed_at,
    }


def replay_fixture_stream(bundles: list[dict[str, Any]], *, observed_at: str = FIXTURE_CLOCK) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for bundle in bundles:
        result = process_pub_ext_bundle(bundle, observed_at=observed_at)
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


def run_publication_external_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    valid_bundle = next(b for b in load_pub_ext_fixtures() if b["bundle_id"] == "pub-ext-valid-release")
    release = process_pub_ext_bundle(valid_bundle, observed_at=observed_at)
    tep = run_pub_ext_fixture_emission(release)
    withdrawal_bundle = next(b for b in load_pub_ext_fixtures() if b["bundle_id"] == "pub-ext-valid-withdrawal")
    withdrawal_path = process_pub_ext_bundle(withdrawal_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(), "status": "recorded", "reason_code": "pub_ext.advisory.release_adapter_fixture",
        "release_result": release, "withdrawal_result": withdrawal_path, "tep_emission": tep,
        "published": False, "live_external_action": False, "permission_granted": False, "observed_at": observed_at,
    }


__all__ = [
    "analyze_pub_ext_fixtures", "process_pub_ext_bundle", "process_publication_release",
    "replay_fixture_stream", "run_publication_external_fixture",
]
