"""Proof artifact writers and the WMBR-05 orchestrator."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hg_runtime.predictive_calibration.calibration_score import (
    build_calibration_record,
    validate_calibration_record,
)
from hg_runtime.predictive_calibration.causal_loader import validate_causal_bundle
from hg_runtime.predictive_calibration.drift_detector import detect_drift
from hg_runtime.predictive_calibration.fixtures import FIXTURE_IDS, outcome_cycle
from hg_runtime.predictive_calibration.prediction_candidate import (
    build_prediction_candidate,
    validate_prediction_candidate,
)
from hg_runtime.predictive_calibration.replay import replay_calibration
from hg_runtime.predictive_calibration.schemas import (
    CALIBRATION_IS_NOT_PROOF,
    CALIBRATION_MANIFEST_SCHEMA,
    CAUSAL_HYPOTHESIS_IS_NOT_TRUTH,
    CONFIDENCE_IS_NOT_AUTHORITY,
    FAILED_PREDICTION_REMAINS_VISIBLE,
    PREDICTION_IS_NOT_VERIFICATION,
    SOURCE_PHASE_ID,
    SUCCESSFUL_PREDICTION_REMAINS_PROVISIONAL,
    SYNTHETIC_OUTCOME_IS_NOT_LIVE_OBSERVATION,
    UNCERTAINTY_IS_NOT_PERMISSION,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.predictive_calibration.synthetic_outcome import (
    build_synthetic_outcome,
    validate_synthetic_outcome,
)
from hg_runtime.predictive_calibration.uncertainty_score import (
    build_uncertainty_score,
    validate_uncertainty_score,
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


def _edges_for_hypothesis(hypothesis_id: str, edges: list[dict]) -> list[str]:
    return sorted(
        e["edge_id"]
        for e in edges
        if e.get("source_hypothesis_id") == hypothesis_id or e.get("hypothesis_id") == hypothesis_id
    )


def _evidence_for_hypothesis(hypothesis: dict) -> list[str]:
    return sorted(
        set(hypothesis.get("supporting_evidence_receipt_ids", []))
        | set(hypothesis.get("contradicting_evidence_receipt_ids", []))
    )


def build_calibration_layer(bundle: dict) -> dict:
    """Run the predictive calibration pipeline over a WMBR-04 causal graph bundle."""
    validate_causal_bundle(bundle)
    hypotheses = sorted(bundle["hypotheses"], key=lambda h: h["hypothesis_id"])
    edges = bundle["edges"]

    prediction_candidates: list[dict] = []
    synthetic_outcomes: list[dict] = []
    calibration_records: list[dict] = []
    uncertainty_scores: list[dict] = []
    drift_records: list[dict] = []

    proposed_index = 0
    hyp_by_id: dict[str, dict] = {}

    for kind_index, hypothesis in enumerate(hypotheses):
        hyp_by_id[hypothesis["hypothesis_id"]] = hypothesis
        edge_ids = _edges_for_hypothesis(hypothesis["hypothesis_id"], edges)
        evidence_ids = _evidence_for_hypothesis(hypothesis)
        candidate = build_prediction_candidate(
            hypothesis=hypothesis,
            edge_ids=edge_ids,
            evidence_receipt_ids=evidence_ids,
            kind_index=kind_index,
        )
        if candidate is None:
            continue
        validate_prediction_candidate(candidate)
        prediction_candidates.append(candidate)

        calibration_record: dict | None = None
        if hypothesis["hypothesis_status"] == "PROPOSED":
            outcome_kind = outcome_cycle()[proposed_index % len(outcome_cycle())]
            fixture_id = FIXTURE_IDS.get(outcome_kind, f"FIXTURE_{outcome_kind}")
            proposed_index += 1
            outcome = build_synthetic_outcome(
                prediction_candidate=candidate,
                outcome_kind=outcome_kind,
                fixture_id=fixture_id,
            )
            validate_synthetic_outcome(outcome)
            synthetic_outcomes.append(outcome)

            calibration_record = build_calibration_record(
                prediction_candidate=candidate,
                synthetic_outcome=outcome,
            )
            validate_calibration_record(calibration_record)
            calibration_records.append(calibration_record)

            candidate = dict(candidate)
            candidate["prediction_status"] = "SYNTHETIC_OUTCOME_ATTACHED"
            candidate["candidate_hash"] = canonical_hash({k: v for k, v in candidate.items() if k != "candidate_hash"})
            prediction_candidates[-1] = candidate

        uncertainty = build_uncertainty_score(
            prediction_candidate=candidate,
            hypothesis=hypothesis,
            calibration_record=calibration_record,
        )
        validate_uncertainty_score(uncertainty)
        uncertainty_scores.append(uncertainty)

        drift = detect_drift(
            prediction_candidate=candidate,
            hypothesis=hypothesis,
            calibration_record=calibration_record,
        )
        if drift is not None:
            drift_records.append(drift)

    prediction_candidates.sort(key=lambda c: c["prediction_candidate_id"])
    synthetic_outcomes.sort(key=lambda s: s["synthetic_outcome_id"])
    calibration_records.sort(key=lambda c: c["calibration_id"])
    uncertainty_scores.sort(key=lambda u: u["uncertainty_id"])
    drift_records.sort(key=lambda d: d["drift_id"])

    mismatches_visible = any(c["score_kind"] == "MISMATCH" for c in calibration_records)
    drift_for_mismatches = any(d["drift_type"] == "SYNTHETIC_MISMATCH" for d in drift_records)

    manifest = {
        "schema": CALIBRATION_MANIFEST_SCHEMA,
        "manifest_id": "wmbr05-calibration-manifest",
        "source_phase": SOURCE_PHASE_ID,
        "source_proof_bundle": bundle.get("source_bundle", "UNKNOWN"),
        "prediction_candidate_count": len(prediction_candidates),
        "synthetic_outcome_count": len(synthetic_outcomes),
        "calibration_record_count": len(calibration_records),
        "uncertainty_score_count": len(uncertainty_scores),
        "drift_record_count": len(drift_records),
        "candidate_hashes": [c["candidate_hash"] for c in prediction_candidates],
        "all_predictions_untested_or_synthetic": True,
        "no_live_observations": True,
        "external_calls_made": False,
        "authority_granted": False,
        "tools_authorized": False,
        "mismatches_remain_visible": mismatches_visible and drift_for_mismatches,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = canonical_hash(manifest)

    replay = replay_calibration(
        prediction_candidates,
        calibration_records,
        uncertainty_scores,
        drift_records,
        manifest,
    )

    summary = {
        "doctrine": "Every model is a compressed civilization artifact.",
        "prediction_candidate_count": len(prediction_candidates),
        "synthetic_outcome_count": len(synthetic_outcomes),
        "calibration_record_count": len(calibration_records),
        "uncertainty_score_count": len(uncertainty_scores),
        "drift_record_count": len(drift_records),
        "mismatches_remain_visible": manifest["mismatches_remain_visible"],
        "drift_records_created_for_mismatches": drift_for_mismatches,
        "all_predictions_untested_or_synthetic": True,
        "no_live_observations": True,
        "replay_preserves_calibration_hashes": replay["replay_preserves_calibration_hashes"],
        "boundaries": {
            "causal_hypothesis_is_not_truth": CAUSAL_HYPOTHESIS_IS_NOT_TRUTH,
            "prediction_is_not_verification": PREDICTION_IS_NOT_VERIFICATION,
            "calibration_is_not_proof": CALIBRATION_IS_NOT_PROOF,
            "uncertainty_is_not_permission": UNCERTAINTY_IS_NOT_PERMISSION,
            "confidence_is_not_authority": CONFIDENCE_IS_NOT_AUTHORITY,
            "synthetic_outcome_is_not_live_observation": SYNTHETIC_OUTCOME_IS_NOT_LIVE_OBSERVATION,
            "failed_prediction_remains_visible": FAILED_PREDICTION_REMAINS_VISIBLE,
            "successful_prediction_remains_provisional": SUCCESSFUL_PREDICTION_REMAINS_PROVISIONAL,
        },
    }
    summary["summary_hash"] = canonical_hash(summary)

    out = {
        "prediction_candidates": prediction_candidates,
        "synthetic_outcomes": synthetic_outcomes,
        "calibration_records": calibration_records,
        "uncertainty_scores": uncertainty_scores,
        "drift_records": drift_records,
        "manifest": manifest,
        "replay": replay,
        "summary": summary,
        "hypotheses": hypotheses,
        "edges": edges,
    }

    for group in (
        "prediction_candidates",
        "synthetic_outcomes",
        "calibration_records",
        "uncertainty_scores",
        "drift_records",
    ):
        for rec in out[group]:
            assert_neutral(rec)
    assert_neutral(manifest)
    return out


def secret_scan(out: dict) -> bool:
    text = json.dumps(out, sort_keys=True, default=str)
    return SECRET_RE.search(text) is None
