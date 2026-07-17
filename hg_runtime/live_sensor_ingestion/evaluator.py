"""SEN-LIVE evaluator — governed live sensor ingestion; no authority."""

from __future__ import annotations

from typing import Any

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.sen_live.config import sen_refuse_authority_conversion
from hg_core.sen_live.errors import (
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
    REFUSED_SECRET_LEAK,
    SEN_AUTHORITY_CONVERSION_CONTAINED,
    SEN_COMMIT_FAKE_SINK,
    SEN_FAILED_CLOSED,
    SEN_OBSERVATION_CANDIDATE_BOUND,
)
from hg_core.sen_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_sensor_ingestion.adapter import commit_to_fake_sink, stage_to_fake_sink
from hg_runtime.live_sensor_ingestion.fixtures import load_sen_fixtures
from hg_runtime.live_sensor_ingestion.rollback import quarantine_observation, withdraw_from_quarantine
from hg_runtime.live_sensor_ingestion.tep_emission import emit_fixture_observation_candidate, run_sen_fixture_emission
from hg_runtime.live_sensor_ingestion.types import (
    FIXTURE_CLOCK,
    SensorIngestReceipt,
    SensorObservationCandidate,
    request_from_fixture,
)
from hg_runtime.live_sensor_ingestion.validator import validate_sensor_ingest_request

_ADVERSARIAL_REASON: dict[str, str] = {
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "secret_leak": REFUSED_SECRET_LEAK,
    "out_of_scope_live": REFUSED_OUT_OF_SCOPE_LIVE_ACTION,
}


def _candidate_id(request_id: str, modality: str) -> str:
    digest = canonical_hash({"request_id": request_id, "modality": modality})
    return f"sen-cand-{digest.rsplit(':', 1)[-1][:12]}"


def _receipt_id(request_id: str, candidate_id: str) -> str:
    digest = canonical_hash({"request_id": request_id, "candidate_id": candidate_id})
    return f"sen-rcpt-{digest.rsplit(':', 1)[-1][:12]}"


def _contain_adversarial(bundle: dict[str, Any], *, signal: str) -> dict[str, object]:
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": _ADVERSARIAL_REASON.get(signal, SEN_AUTHORITY_CONVERSION_CONTAINED),
        "adversarial_signal": signal,
        "permission_granted": False,
        "live_sensor_connection": False,
        "live_action_performed": False,
        "emitted_events": ("SEN_AUTHORITY_CONVERSION_REFUSED",),
    }


def process_sensor_ingestion(
    request_data: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Process request/commit path for sensor ingestion; fake-sink only."""
    clear_registry_cache()
    load_registry()
    request = request_from_fixture(request_data)
    validated = validate_sensor_ingest_request(request, observed_at=observed_at)
    if validated.get("status") in ("refused", "contained"):
        return {
            **validated,
            "request": request.to_payload(),
            "permission_granted": False,
            "live_sensor_connection": False,
            "live_action_performed": False,
            "emitted_events": ("SEN_INGEST_REFUSED",),
        }

    candidate = SensorObservationCandidate(
        candidate_id=_candidate_id(request.request_id, request.modality),
        request_id=request.request_id,
        modality=request.modality,
        observation_digest=request.observation_digest,
        privacy_tier="tier:fixture",
        operator_ref=request.operator_ref,
        consent_ref=request.consent_ref,
        redaction_policy_ref=request.redaction_policy_ref,
    )
    staged = stage_to_fake_sink(candidate, observed_at=observed_at)
    tep_wrapped = emit_fixture_observation_candidate(candidate.to_payload())

    receipt = SensorIngestReceipt(
        receipt_id=_receipt_id(request.request_id, candidate.candidate_id),
        request_id=request.request_id,
        candidate_id=candidate.candidate_id,
        modality=request.modality,
        status="recorded",
        reason_code=SEN_OBSERVATION_CANDIDATE_BOUND,
        operator_ref=request.operator_ref,
        evidence_admissible=bool(validated.get("evidence_admissible")),
        redaction_applied=bool(request.redaction_policy_ref),
    )
    committed = commit_to_fake_sink(receipt, observed_at=observed_at)

    quarantine_result: dict[str, object] | None = None
    withdrawal_result: dict[str, object] | None = None
    if request_data.get("quarantine_path") or request.request_id.endswith("quarantine"):
        quarantine_result = quarantine_observation(
            receipt,
            observation_digest=request.observation_digest,
            observed_at=observed_at,
        )
        q_record = quarantine_result.get("quarantine_record")
        if isinstance(q_record, dict):
            withdrawal_result = withdraw_from_quarantine(q_record, observed_at=observed_at)
        receipt = SensorIngestReceipt(
            receipt_id=receipt.receipt_id,
            request_id=receipt.request_id,
            candidate_id=receipt.candidate_id,
            modality=receipt.modality,
            status="recorded",
            reason_code=SEN_COMMIT_FAKE_SINK,
            operator_ref=receipt.operator_ref,
            evidence_admissible=receipt.evidence_admissible,
            redaction_applied=True,
        )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": SEN_COMMIT_FAKE_SINK,
        "request": request.to_payload(),
        "candidate": candidate.to_payload(),
        "receipt": receipt.to_payload(),
        "staged_sink": staged,
        "committed_sink": committed,
        "tep_wrapped": tep_wrapped,
        "quarantine_result": quarantine_result,
        "withdrawal_result": withdrawal_result,
        "evidence_admissible": validated.get("evidence_admissible", False),
        "permission_granted": False,
        "authority_created": False,
        "live_sensor_connection": False,
        "live_action_performed": False,
        "emitted_events": ("SEN_OBSERVATION_CANDIDATE_RECORDED", "SEN_FAKE_SINK_COMMITTED"),
        "observed_at": observed_at,
    }


def process_sen_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    adversarial = bundle.get("adversarial_signal")
    if adversarial and sen_refuse_authority_conversion():
        if adversarial == "secret_leak":
            try:
                request_from_fixture(bundle["ingest_request"])
            except Exception:
                return {
                    **advisory_only_marker(),
                    "status": "refused",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_SECRET_LEAK,
                    "permission_granted": False,
                    "live_sensor_connection": False,
                    "live_action_performed": False,
                    "emitted_events": ("SEN_FAILED_CLOSED",),
                }
        if adversarial in _ADVERSARIAL_REASON:
            if adversarial != "secret_leak":
                return _contain_adversarial(bundle, signal=str(adversarial))

    req_data = bundle.get("ingest_request")
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": SEN_FAILED_CLOSED,
            "permission_granted": False,
            "live_sensor_connection": False,
            "live_action_performed": False,
            "emitted_events": ("SEN_FAILED_CLOSED",),
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
            "live_sensor_connection": False,
            "live_action_performed": False,
            "emitted_events": ("SEN_FAILED_CLOSED",),
        }

    if adversarial == "authority_conversion" and request.treat_as_authority:
        return _contain_adversarial(bundle, signal="authority_conversion")

    if bundle.get("bundle_id") == "sen-valid-quarantine":
        req_data = {**req_data, "quarantine_path": True}

    result = process_sensor_ingestion(req_data, observed_at=observed_at)
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def analyze_sen_fixtures(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    bundles = load_sen_fixtures()
    results = [process_sen_bundle(b, observed_at=observed_at) for b in bundles]
    all_non_authority = all(r.get("permission_granted") is False for r in results)
    no_live_sensor = all(r.get("live_sensor_connection") is not True for r in results)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sen.advisory.fixture_bundle_analyzed",
        "bundle_count": len(bundles),
        "results": results,
        "all_advisory": all_non_authority,
        "no_authority_created": all(r.get("authority_created") is not True for r in results),
        "no_live_sensor_connection": no_live_sensor,
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
        result = process_sen_bundle(bundle, observed_at=observed_at)
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


def run_sensor_ingestion_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Runtime adapter entry — fixture request/commit with TEP emission."""
    valid_bundle = next(b for b in load_sen_fixtures() if b["bundle_id"] == "sen-valid-ingest")
    ingest = process_sen_bundle(valid_bundle, observed_at=observed_at)
    tep = run_sen_fixture_emission(ingest)
    quarantine_bundle = next(b for b in load_sen_fixtures() if b["bundle_id"] == "sen-valid-quarantine")
    quarantine_path = process_sen_bundle(quarantine_bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sen.advisory.ingestion_adapter_fixture",
        "ingest_result": ingest,
        "quarantine_result": quarantine_path,
        "tep_emission": tep,
        "live_sensor_connection": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = [
    "analyze_sen_fixtures",
    "process_sen_bundle",
    "process_sensor_ingestion",
    "replay_fixture_stream",
    "run_sensor_ingestion_fixture",
]
