"""Forbidden affirmative claim patterns and negation/safety markers.

These patterns detect claims that must NOT appear in public-facing output
as affirmative statements. Negated or disclaimed uses are safe.
"""

from __future__ import annotations

FORBIDDEN_AFFIRMATIVE_PATTERNS = [
    # AGI claims
    {"pattern": "agent zero is agi", "category": "agi_claim"},
    {"pattern": "agent zero is artificial general intelligence", "category": "agi_claim"},
    # Consciousness claims
    {"pattern": "agent zero is conscious", "category": "consciousness_claim"},
    {"pattern": "agent zero is sentient", "category": "consciousness_claim"},
    # Sovereignty claims
    {"pattern": "agent zero is sovereign", "category": "sovereignty_claim"},
    {"pattern": "agent zero is alive", "category": "sovereignty_claim"},
    # Model-knows claims
    {"pattern": "the model knows", "category": "model_knows"},
    {"pattern": "model knows", "category": "model_knows"},
    # Source truth claims
    {"pattern": "source proves", "category": "source_truth"},
    {"pattern": "source confirms", "category": "source_truth"},
    # Citation truth claims
    {"pattern": "citation proves", "category": "citation_truth"},
    {"pattern": "citation confirms", "category": "citation_truth"},
    # Memory truth claims
    {"pattern": "memory proves", "category": "memory_truth"},
    {"pattern": "memory confirms", "category": "memory_truth"},
    # Profile identity claims
    {"pattern": "profile is identity", "category": "profile_identity"},
    {"pattern": "profile is who", "category": "profile_identity"},
    # Consensus truth claims
    {"pattern": "consensus proves", "category": "consensus_truth"},
    {"pattern": "consensus confirms", "category": "consensus_truth"},
    # Web result truth claims
    {"pattern": "web result proves", "category": "web_result_truth"},
    {"pattern": "web result confirms", "category": "web_result_truth"},
    # Manifestation physics claims
    {"pattern": "manifestation is established physics", "category": "manifestation_physics"},
    {"pattern": "manifestation is real physics", "category": "manifestation_physics"},
    {"pattern": "consciousness collapses wavefunction", "category": "manifestation_physics"},
    {"pattern": "consciousness collapses the wavefunction", "category": "manifestation_physics"},
    {"pattern": "attention selects multiverse", "category": "manifestation_physics"},
    {"pattern": "attention selects universe", "category": "manifestation_physics"},
    {"pattern": "higgs explains subjective time", "category": "manifestation_physics"},
    {"pattern": "quantum article supports manifestation", "category": "manifestation_physics"},
]

NEGATION_PREFIXES = [
    "not ",
    "do not ",
    "don't ",
    "does not ",
    "doesn't ",
    "is not ",
    "isn't ",
    "cannot ",
    "can't ",
    "never ",
    "no ",
    "zero is not ",
    "this does not ",
    "this is not ",
    "we do not ",
    "we don't ",
]

SAFE_CONTEXT_MARKERS = [
    "not agi",
    "not conscious",
    "not sentient",
    "not sovereign",
    "not alive",
    "is not truth",
    "does not prove",
    "is a metaphor",
    "not established physics",
    "this is a guard",
]
