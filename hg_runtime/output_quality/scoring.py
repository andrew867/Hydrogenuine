"""Slop, repetition, and specificity scoring for output quality."""

from __future__ import annotations

import re
from collections import Counter

SLOP_PHRASES = [
    "this hypothesis suggests",
    "further research is needed",
    "more research is needed",
    "in conclusion",
    "it is important to note",
    "as mentioned above",
    "it should be noted",
    "it is worth noting",
    "this is a very important",
    "this is an interesting",
]

FILLER_PATTERNS = [
    r"\bin\s+conclusion\b",
    r"\bas\s+we\s+can\s+see\b",
    r"\bit\s+is\s+clear\s+that\b",
    r"\bthis\s+highlights\b",
    r"\boverall[,.]",
]


def slop_score(content: str) -> float:
    if not content:
        return 1.0
    lower = content.lower()
    hits = sum(1 for phrase in SLOP_PHRASES if phrase in lower)
    hits += sum(1 for pat in FILLER_PATTERNS if re.search(pat, lower))
    return min(1.0, hits / max(1, len(content) / 200))


def repetition_score(content: str) -> float:
    if not content or len(content) < 50:
        return 0.0
    sentences = re.split(r'[.!?\n]+', content)
    sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 10]
    if len(sentences) < 2:
        return 0.0
    counts = Counter(sentences)
    duplicates = sum(c - 1 for c in counts.values() if c > 1)
    return min(1.0, duplicates / max(1, len(sentences)))


def specificity_score(content: str) -> float:
    if not content:
        return 0.0
    indicators = 0
    lower = content.lower()
    if re.search(r'\d+\.?\d*\s*(hz|mhz|ghz|thz|ev|mev|gev|tev|nm|mm|cm|m|kg|s|ms|µs)', lower):
        indicators += 2
    if re.search(r'\d+\.?\d*\s*[×x]\s*10', content):
        indicators += 2
    if any(w in lower for w in ["measur", "experiment", "protocol", "apparatus", "sample size"]):
        indicators += 1
    if any(w in lower for w in ["falsif", "predict", "expected if real", "expected if false"]):
        indicators += 1
    if re.search(r'[A-Z][a-z]+ et al\.', content) or re.search(r'\(\d{4}\)', content):
        indicators += 1
    if len(content) > 800:
        indicators += 1
    return min(1.0, indicators / 6.0)
