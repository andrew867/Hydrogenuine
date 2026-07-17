"""SQP-2 non-authoritative source quality scorer."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.quality_features import build_quality_feature_record
from hg_runtime.source_quality_provenance.quality_policy import QUALITY_POLICY
from hg_runtime.source_quality_provenance.schemas import QUALITY_BANDS, assert_neutral, neutral_flags
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def score_band_for_features(features: dict[str, bool]) -> str:
    if features.get("SECURITY_FINDING_PRESENT"):
        return "BLOCKED"
    if features.get("CONFLICT_SIGNAL_PRESENT") or features.get("QUARANTINE_HISTORY_PRESENT"):
        return "CONFLICTED_OR_QUARANTINED"
    if features.get("HAS_REVIEW_DECISION") and features.get("HAS_SOURCE_IDENTITY") and features.get("HAS_STABLE_FINGERPRINT"):
        return "REVIEWED_USABLE"
    if features.get("HAS_SOURCE_IDENTITY") and features.get("HAS_STABLE_FINGERPRINT") and features.get("HAS_EXCERPT_BOUNDARY"):
        return "STRUCTURALLY_USABLE"
    if any(features.values()):
        return "LOW_INFORMATION"
    return "UNRATED"


def build_quality_score_from_features(source_id: str, features: dict[str, bool]) -> tuple[dict, dict]:
    feature_record = build_quality_feature_record(source_id=source_id, features=features)
    quality_band = score_band_for_features(feature_record["features"])
    if quality_band not in QUALITY_BANDS:
        raise ValueError(f"unknown_quality_band:{quality_band}")
    record = {
        "schema_version": "1",
        "record_type": "source_quality_score_v1",
        "source_id": source_id,
        "quality_band": quality_band,
        "quality_policy_id": QUALITY_POLICY["policy_id"],
        "quality_feature_hash": feature_record["feature_hash"],
        "quality_feature_names": [name for name, present in feature_record["features"].items() if present],
        "score_rationale": [
            "metadata-only SQP-2 fixture score",
            "factual truth, certainty, authority, action, deletion, and belief promotion excluded",
        ],
        "scored_at": FIXED_TIME,
        "doctrine_note": "Source quality is not truth.",
        "high_score_is_certainty": False,
        "low_score_is_false": False,
        "blocked_is_deletion": False,
        "score_authorizes_action": False,
        "score_authorizes_tools": False,
        "score_promotes_belief": False,
        "score_overrides_operator_review": False,
        "score_hides_contradictions": False,
        **neutral_flags(),
    }
    record["quality_hash"] = record_hash(record)
    assert_neutral(record)
    return feature_record, record


def score_sources(feature_sets: dict[str, dict[str, bool]]) -> dict:
    features: list[dict] = []
    scores: list[dict] = []
    for source_id, source_features in feature_sets.items():
        feature_record, score = build_quality_score_from_features(source_id, source_features)
        features.append(feature_record)
        scores.append(score)
    return {"source_quality_feature_records": features, "source_quality_scores": scores}
