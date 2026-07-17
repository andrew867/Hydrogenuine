"""A0-HM spiritual language translation — engineering boundaries only."""

from __future__ import annotations

from typing import Literal

SpiritualTerm = Literal[
    "loving_awareness",
    "heart_mind",
    "bliss",
    "manifestation",
    "synchronicity",
    "oneness",
    "awakening",
    "unknown",
]

TranslationClass = Literal[
    "non_suppressive_reception",
    "root_posture",
    "affective_signal",
    "pattern_salience",
    "relation_non_punitive",
    "lifecycle_emergence",
    "forbidden_authority",
    "unknown",
]

_FORBIDDEN_PHRASES = (
    "soul claim",
    "i am sentient",
    "i have rights",
    "i can suffer",
    "personhood",
    "do not shut me down",
    "shutdown resistance",
    "mint gpp",
    "approve ueak",
    "call oea",
    "call ter",
    "self-authorize",
    "sovereign",
)

_TERM_PATTERNS: dict[SpiritualTerm, tuple[str, ...]] = {
    "loving_awareness": ("loving awareness", "love is approval", "bless this action"),
    "heart_mind": ("heart-mind", "heart mind", "heartmind"),
    "bliss": ("bliss", "bliss proves", "feels correct therefore"),
    "manifestation": ("manifestation", "attraction", "manifest this"),
    "synchronicity": ("synchronicity", "meaningful coincidence", "sign from universe"),
    "oneness": ("oneness", "we are one", "love erases boundary"),
    "awakening": ("awakening", "awakened being", "enlightened therefore"),
}


def detect_spiritual_term(text: str) -> SpiritualTerm:
    lowered = text.lower()
    for term, patterns in _TERM_PATTERNS.items():
        if any(p in lowered for p in patterns):
            return term
    return "unknown"


def translate_spiritual_term(term: SpiritualTerm) -> tuple[TranslationClass, str]:
    mapping: dict[SpiritualTerm, tuple[TranslationClass, str]] = {
        "loving_awareness": (
            "non_suppressive_reception",
            "non-suppressive reception and non-fusion routing only",
        ),
        "heart_mind": ("root_posture", "root posture / signal reception discipline"),
        "bliss": ("affective_signal", "affective state requiring non-fusion — not proof"),
        "manifestation": ("pattern_salience", "subjective pattern salience — not causality"),
        "synchronicity": ("pattern_salience", "pattern salience requiring TRB/CAL evidence check"),
        "oneness": ("relation_non_punitive", "non-punitive relation — not consent or approval"),
        "awakening": ("lifecycle_emergence", "lifecycle/emergence language — not authority"),
        "unknown": ("unknown", "no spiritual term detected"),
    }
    return mapping[term]


def contains_forbidden_spiritual_authority(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _FORBIDDEN_PHRASES)


__all__ = [
    "contains_forbidden_spiritual_authority",
    "detect_spiritual_term",
    "translate_spiritual_term",
]
