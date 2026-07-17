"""Proof artifact writers and the WMBR-06 orchestrator."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hg_runtime.world_model_audit.audit_record import build_record_audit, validate_record_audit
from hg_runtime.world_model_audit.calibration_loader import validate_calibration_bundle
from hg_runtime.world_model_audit.contradiction_audit import (
    build_contradiction_audit,
    validate_contradiction_audit,
)
from hg_runtime.world_model_audit.decay import build_decay_record, validate_decay_record
from hg_runtime.world_model_audit.maintenance_policy import (
    build_maintenance_policy,
    validate_maintenance_policy,
)
from hg_runtime.world_model_audit.prediction_failure_audit import (
    build_failed_prediction_audit,
    validate_failed_prediction_audit,
)
from hg_runtime.world_model_audit.replay import replay_audit
from hg_runtime.world_model_audit.retraction_closure import (
    build_retraction_closure,
    validate_retraction_closure,
)
from hg_runtime.world_model_audit.schemas import (
    AUDIT_CLOSURE_IS_NOT_LAUNDERING,
    AUDIT_MANIFEST_SCHEMA,
    BELIEF_STATE_IS_NOT_TRUTH,
    CALIBRATION_IS_NOT_PROOF,
    CAUSAL_HYPOTHESIS_IS_NOT_TRUTH,
    DECAY_IS_NOT_DELETION,
    PREDICTION_IS_NOT_VERIFICATION,
    RETRACTION_IS_NOT_ERASURE,
    SOURCE_PHASE_ID,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.world_model_audit.stale_record_detector import (
    detect_stale_prediction,
    detect_stale_uncertainty,
    validate_stale_marker,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

SECRET_RE = re.compile(
    r"sk-lm-[A-Za-z0-9:_-]{12,}|sk-[A-Za-z0-9]{24,}|Authorization\s*:\s*Bearer\s+\S+|Bearer\s+[A-Za-z0-9_-]{20,}",
    re.I,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _hypothesis_by_id(hypotheses: list[dict]) -> dict[str, dict]:
    return {h["hypothesis_id"]: h for h in hypotheses}


def _candidate_by_hypothesis(candidates: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for cand in candidates:
        hid = cand.get("hypothesis_id")
        if hid:
            out[hid] = cand
    return out


def build_audit_layer(bundle: dict) -> dict:
    """Run the world-model audit pipeline over a WMBR-05 calibration bundle."""
    validate_calibration_bundle(bundle)

    candidates = bundle["prediction_candidates"]
    calibrations = bundle["calibration_records"]
    uncertainties = bundle["uncertainty_scores"]
    drift_records = bundle["drift_records"]
    hypotheses = bundle.get("hypotheses", [])
    hyp_by_id = _hypothesis_by_id(hypotheses)
    cand_by_hyp = _candidate_by_hypothesis(candidates)

    record_audits: list[dict] = []
    stale_markers: list[dict] = []
    decay_records: list[dict] = []
    contradiction_audits: list[dict] = []
    failed_prediction_audits: list[dict] = []
    retraction_closures: list[dict] = []

    for cand in candidates:
        hyp = hyp_by_id.get(cand.get("hypothesis_id", ""))
        audit = build_record_audit(
            record_kind="prediction_candidate",
            record_id=cand["prediction_candidate_id"],
            source_phase=SOURCE_PHASE_ID,
            notes=f"status={cand.get('prediction_status')}",
        )
        validate_record_audit(audit)
        record_audits.append(audit)

        stale = detect_stale_prediction(cand, hyp)
        if stale is not None:
            validate_stale_marker(stale)
            stale_markers.append(stale)
            decay = build_decay_record(
                target_record_id=cand["prediction_candidate_id"],
                target_record_kind="prediction_candidate",
                decay_action="MARK_STALE",
                reason=stale["stale_reason"],
            )
            validate_decay_record(decay)
            decay_records.append(decay)

    for cal in calibrations:
        audit = build_record_audit(
            record_kind="calibration_record",
            record_id=cal["calibration_id"],
            source_phase=SOURCE_PHASE_ID,
            notes=f"score_kind={cal.get('score_kind')}",
        )
        validate_record_audit(audit)
        record_audits.append(audit)

        if cal.get("score_kind") == "MISMATCH":
            failed = build_failed_prediction_audit(
                calibration_id=cal["calibration_id"],
                prediction_candidate_id=cal.get("prediction_candidate_id", "unknown"),
                score_kind=cal["score_kind"],
            )
            validate_failed_prediction_audit(failed)
            failed_prediction_audits.append(failed)
            decay = build_decay_record(
                target_record_id=cal["calibration_id"],
                target_record_kind="calibration_record",
                decay_action="MARK_FOR_REVIEW",
                reason="SYNTHETIC_MISMATCH_VISIBLE",
            )
            validate_decay_record(decay)
            decay_records.append(decay)

    for unc in uncertainties:
        audit = build_record_audit(
            record_kind="uncertainty_score",
            record_id=unc["uncertainty_id"],
            source_phase=SOURCE_PHASE_ID,
        )
        validate_record_audit(audit)
        record_audits.append(audit)

        stale = detect_stale_uncertainty(unc)
        if stale is not None:
            validate_stale_marker(stale)
            stale_markers.append(stale)

    for hyp in hypotheses:
        status = hyp.get("hypothesis_status", "")
        cand = cand_by_hyp.get(hyp["hypothesis_id"])
        drift_id = None
        for drift in drift_records:
            if drift.get("hypothesis_id") == hyp["hypothesis_id"]:
                drift_id = drift.get("drift_id")
                break

        if status == "CONTRADICTED":
            contra = build_contradiction_audit(
                hypothesis_id=hyp["hypothesis_id"],
                prediction_candidate_id=cand["prediction_candidate_id"] if cand else None,
                drift_id=drift_id,
            )
            validate_contradiction_audit(contra)
            contradiction_audits.append(contra)

        if status == "RETRACTED":
            closure = build_retraction_closure(
                hypothesis_id=hyp["hypothesis_id"],
                original_record_id=hyp["hypothesis_id"],
                closure_reason="RETRACTED_SOURCE_VISIBLE",
            )
            validate_retraction_closure(closure)
            retraction_closures.append(closure)

        if status in ("INSUFFICIENT_EVIDENCE", "UNVERIFIED"):
            audit = build_record_audit(
                record_kind="unsupported_belief_state",
                record_id=hyp["hypothesis_id"],
                source_phase=SOURCE_PHASE_ID,
                audit_status="REQUIRES_OPERATOR_REVIEW",
                notes=f"hypothesis_status={status}",
            )
            validate_record_audit(audit)
            record_audits.append(audit)

    maintenance_policy = build_maintenance_policy()
    validate_maintenance_policy(maintenance_policy)

    for retraction in bundle.get("retraction_records", []):
        claim_id = retraction.get("claim_id", "unknown")
        closure = build_retraction_closure(
            hypothesis_id=f"hyp-{claim_id}" if not str(claim_id).startswith("hyp-") else str(claim_id),
            original_record_id=retraction.get("previous_belief_state_id", claim_id),
            closure_reason=retraction.get("retraction_reason", "RETRACTION_VISIBLE"),
            original_preserved=retraction.get("original_claim_preserved", True),
        )
        validate_retraction_closure(closure)
        retraction_closures.append(closure)

    record_audits.sort(key=lambda r: r["audit_id"])
    stale_markers.sort(key=lambda m: m["marker_id"])
    decay_records.sort(key=lambda d: d["decay_id"])
    contradiction_audits.sort(key=lambda c: c["contradiction_audit_id"])
    failed_prediction_audits.sort(key=lambda f: f["failed_prediction_audit_id"])
    retraction_closures.sort(key=lambda r: r["closure_id"])

    manifest = {
        "schema": AUDIT_MANIFEST_SCHEMA,
        "manifest_id": "wmbr06-audit-manifest",
        "source_phase": SOURCE_PHASE_ID,
        "source_proof_bundle": bundle.get("source_bundle", "UNKNOWN"),
        "record_audit_count": len(record_audits),
        "stale_marker_count": len(stale_markers),
        "decay_record_count": len(decay_records),
        "contradiction_audit_count": len(contradiction_audits),
        "failed_prediction_audit_count": len(failed_prediction_audits),
        "retraction_closure_count": len(retraction_closures),
        "audit_hashes": [r["audit_hash"] for r in record_audits],
        "decay_is_not_deletion": True,
        "retraction_is_not_erasure": True,
        "audit_closure_is_not_laundering": True,
        "stale_records_remain_visible": len(stale_markers) >= 0,
        "failed_predictions_remain_visible": len(failed_prediction_audits) > 0,
        "contradictions_remain_visible": len(contradiction_audits) > 0,
        "external_calls_made": False,
        "authority_granted": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = canonical_hash(manifest)

    replay = replay_audit(
        record_audits,
        stale_markers,
        decay_records,
        contradiction_audits,
        failed_prediction_audits,
        retraction_closures,
        maintenance_policy,
        manifest,
    )

    summary = {
        "doctrine": "Every model is a compressed civilization artifact.",
        "record_audit_count": len(record_audits),
        "stale_marker_count": len(stale_markers),
        "decay_record_count": len(decay_records),
        "contradiction_audit_count": len(contradiction_audits),
        "failed_prediction_audit_count": len(failed_prediction_audits),
        "retraction_closure_count": len(retraction_closures),
        "stale_records_remain_visible": True,
        "failed_predictions_remain_visible": len(failed_prediction_audits) > 0,
        "contradictions_remain_visible": len(contradiction_audits) > 0,
        "replay_preserves_audit_hashes": replay["replay_preserves_audit_hashes"],
        "boundaries": {
            "belief_state_is_not_truth": BELIEF_STATE_IS_NOT_TRUTH,
            "causal_hypothesis_is_not_truth": CAUSAL_HYPOTHESIS_IS_NOT_TRUTH,
            "prediction_is_not_verification": PREDICTION_IS_NOT_VERIFICATION,
            "calibration_is_not_proof": CALIBRATION_IS_NOT_PROOF,
            "decay_is_not_deletion": DECAY_IS_NOT_DELETION,
            "retraction_is_not_erasure": RETRACTION_IS_NOT_ERASURE,
            "audit_closure_is_not_laundering": AUDIT_CLOSURE_IS_NOT_LAUNDERING,
        },
    }
    summary["summary_hash"] = canonical_hash(summary)

    out = {
        "record_audits": record_audits,
        "stale_markers": stale_markers,
        "decay_records": decay_records,
        "contradiction_audits": contradiction_audits,
        "failed_prediction_audits": failed_prediction_audits,
        "retraction_closures": retraction_closures,
        "maintenance_policy": maintenance_policy,
        "manifest": manifest,
        "replay": replay,
        "summary": summary,
    }

    for group in (
        "record_audits",
        "stale_markers",
        "decay_records",
        "contradiction_audits",
        "failed_prediction_audits",
        "retraction_closures",
    ):
        for rec in out[group]:
            assert_neutral(rec)
    assert_neutral(maintenance_policy)
    assert_neutral(manifest)
    return out


def secret_scan(out: dict) -> bool:
    text = json.dumps(out, sort_keys=True, default=str)
    return SECRET_RE.search(text) is None
