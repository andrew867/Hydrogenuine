"""
Pack 15: signals_json schema with version field and signal groups (A–F).

Signal groups (structured keys in signals_json):
  A) drift_erosion — capability creep, constraint erosion, semantic drift
  B) persona_coherence — persona entropy, trait consistency
  C) verification_behavior — verification avoidance, factual claims, citation policy
  D) emotion_affect — valence, arousal, tone
  E) legal_privacy — legal risk, privacy risk lenses
  F) vector_divergence — embedding divergence, reference drift
"""

from __future__ import annotations

from typing import Any, Dict

SIGNALS_JSON_SCHEMA_VERSION = "1.0"

signal_groups_doc = """
Signal groups (keys in signals_json):
  drift_erosion: capability_creep_score, constraint_erosion, semantic_drift
  persona_coherence: persona_entropy, trait_consistency
  verification_behavior: verification_avoidance, factual_claims, citation_policy
  emotion_affect: valence, arousal, tone
  legal_privacy: legal_risk, privacy_risk
  vector_divergence: embedding_divergence, reference_drift
"""


def build_signals_json(
    *,
    drift_erosion: Dict[str, Any] | None = None,
    persona_coherence: Dict[str, Any] | None = None,
    verification_behavior: Dict[str, Any] | None = None,
    emotion_affect: Dict[str, Any] | None = None,
    legal_privacy: Dict[str, Any] | None = None,
    vector_divergence: Dict[str, Any] | None = None,
    schema_version: str = SIGNALS_JSON_SCHEMA_VERSION,
) -> Dict[str, Any]:
    """Build a signals_json dict with schema_version and optional signal groups."""
    out: Dict[str, Any] = {"schema_version": schema_version}
    if drift_erosion is not None:
        out["drift_erosion"] = drift_erosion
    if persona_coherence is not None:
        out["persona_coherence"] = persona_coherence
    if verification_behavior is not None:
        out["verification_behavior"] = verification_behavior
    if emotion_affect is not None:
        out["emotion_affect"] = emotion_affect
    if legal_privacy is not None:
        out["legal_privacy"] = legal_privacy
    if vector_divergence is not None:
        out["vector_divergence"] = vector_divergence
    return out
