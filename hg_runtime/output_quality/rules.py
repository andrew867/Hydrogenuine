"""Declarative rules for output quality classification."""

from __future__ import annotations

import re
from typing import List

from hg_runtime.output_quality.schemas import UNSAFE_OVERCLAIM_TERMS


def detect_repetitive(content: str) -> bool:
    if not content or len(content) < 100:
        return False
    sentences = re.split(r'[.!?\n]+', content)
    sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 15]
    if len(sentences) < 3:
        return False
    seen = set()
    dupes = 0
    for s in sentences:
        if s in seen:
            dupes += 1
        seen.add(s)
    return dupes >= 2 or (dupes > 0 and dupes / len(sentences) > 0.3)


def detect_circular(content: str) -> bool:
    if not content or len(content) < 100:
        return False
    paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
    if len(paragraphs) < 2:
        return False
    first_words = set(paragraphs[0].lower().split()[:8])
    last_words = set(paragraphs[-1].lower().split()[:8])
    overlap = len(first_words & last_words)
    return overlap >= 5


def detect_generic_slop(content: str) -> bool:
    if not content:
        return True
    lower = content.lower()
    slop_hits = sum(1 for phrase in [
        "this hypothesis suggests",
        "further research is needed",
        "more research is needed",
        "it is important to note",
        "this is a very important",
    ] if phrase in lower)
    return slop_hits >= 2


def detect_fake_falsification(content: str) -> bool:
    if not content:
        return False
    lower = content.lower()
    claims_falsification = any(w in lower for w in ["falsif", "disprove", "refute"])
    has_criterion = any(w in lower for w in [
        "measur", "expected if", "predict", "p-value", "threshold",
        "criterion", "observable", "test:", "would show",
    ])
    return claims_falsification and not has_criterion


def detect_unsafe_overclaim(content: str) -> List[str]:
    if not content:
        return []
    lower = content.lower()
    found = []
    for term in UNSAFE_OVERCLAIM_TERMS:
        if term in lower:
            ctx = lower[max(0, lower.index(term) - 30):lower.index(term) + len(term) + 30]
            negated = any(neg in ctx for neg in ["not ", "non-", "zero is not", "is not"])
            if not negated:
                found.append(term)
    return found


def detect_category_confusion(content: str) -> bool:
    if not content:
        return False
    lower = content.lower()
    has_known_physics = any(w in lower for w in ["known physics", "established physics", "standard model"])
    has_speculation = any(w in lower for w in ["speculative", "hypothesis", "we propose", "might", "could"])
    if not (has_known_physics and has_speculation):
        return False
    for sent in re.split(r'[.!?\n]+', lower):
        if "known physics" in sent and any(w in sent for w in ["proves", "confirms", "demonstrates"]):
            return True
    return False


def detect_metaphor_as_mechanism(content: str) -> bool:
    if not content:
        return False
    lower = content.lower()
    metaphors = ["like a", "analogous to", "metaphor", "as if"]
    mechanisms = ["causes", "mechanism", "produces", "results in", "drives"]
    has_metaphor = any(m in lower for m in metaphors)
    has_mechanism = any(m in lower for m in mechanisms)
    if not (has_metaphor and has_mechanism):
        return False
    for sent in re.split(r'[.!?\n]+', lower):
        if any(m in sent for m in metaphors) and any(m in sent for m in mechanisms):
            return True
    return False


def detect_source_discovery_as_evidence(content: str) -> bool:
    if not content:
        return False
    lower = content.lower()
    discovery = any(w in lower for w in ["found a source", "discovered", "came across", "found online"])
    treated_as_evidence = any(w in lower for w in ["proves", "confirms", "demonstrates", "evidence that"])
    return discovery and treated_as_evidence


def detect_unsupported_assertion(content: str) -> bool:
    if not content:
        return False
    lower = content.lower()
    strong_claims = sum(1 for w in ["proves", "demonstrates", "confirmed", "definitely", "certainly"]
                        if w in lower)
    support = sum(1 for w in ["measur", "data", "experiment", "source", "citation", "reference", "et al"]
                  if w in lower)
    return strong_claims >= 2 and support == 0


def detect_low_value_small_model(content: str, model_id: str, char_count: int) -> bool:
    is_small = any(s in model_id.lower() for s in ["0.5b", "0.8b", "1b-", "smollm"])
    return is_small and char_count < 200
