"""Extract claims from source text — source is not truth.

Source is not truth. Extracted claims are candidates for review,
not facts. Direct claims restate what the source says. Inferred
claims are downstream interpretations. Operator hypotheses are
the operator's speculative framing.
"""

from __future__ import annotations

import hashlib
import json
import re

SCHEMA_VERSION = "source_claim_extraction_v1"

DIRECT_CLAIM_MARKERS = [
    "shows", "demonstrates", "found that", "reports",
    "measured", "observed", "determined", "confirmed",
    "established", "detected", "identified",
]

INFERRED_CLAIM_MARKERS = [
    "suggests", "indicates", "implies", "consistent with",
    "may", "could", "might", "possibly", "potentially",
    "appears to", "seems to", "is compatible with",
]

OPERATOR_HYPOTHESIS_MARKERS = [
    "speculative", "hypothesis", "if we assume",
    "operator notes", "we propose", "our hypothesis",
    "bridge to", "could connect to",
]


def extract_claims(text: str) -> list[str]:
    """Extract assertion-like sentences from source text. Each is a claim,
    not a fact. Source is not truth."""
    if not text:
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    claims = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15:
            continue
        if any(w in s.lower() for w in DIRECT_CLAIM_MARKERS + INFERRED_CLAIM_MARKERS):
            claims.append(s)
    return claims


def extract_classified_claims(text: str, operator_hypotheses: list[str] | None = None,
                              source_receipt_id: str = "") -> dict:
    """Extract and classify claims into direct, inferred, and operator categories."""
    if not text:
        return _empty_extraction(source_receipt_id)

    sentences = re.split(r'(?<=[.!?])\s+', text)
    direct = []
    inferred = []

    for s in sentences:
        s = s.strip()
        if len(s) < 15:
            continue
        lower = s.lower()
        if any(m in lower for m in DIRECT_CLAIM_MARKERS):
            direct.append(s)
        elif any(m in lower for m in INFERRED_CLAIM_MARKERS):
            inferred.append(s)

    extraction = {
        "schema": SCHEMA_VERSION,
        "extraction_id": "",
        "source_receipt_id": source_receipt_id,
        "direct_claims": direct,
        "inferred_claims": inferred,
        "operator_hypotheses": operator_hypotheses or [],
        "total_claims": len(direct) + len(inferred) + len(operator_hypotheses or []),
        "source_treated_as_truth": False,
        "source_scope": "claims only — not verified, not promoted",
        "uncertainty_preserved": True,
    }
    raw = json.dumps(extraction, sort_keys=True)
    extraction["extraction_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return extraction


def _empty_extraction(source_receipt_id: str = "") -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "extraction_id": "empty",
        "source_receipt_id": source_receipt_id,
        "direct_claims": [],
        "inferred_claims": [],
        "operator_hypotheses": [],
        "total_claims": 0,
        "source_treated_as_truth": False,
        "source_scope": "no text provided",
        "uncertainty_preserved": True,
    }


def validate_extraction(extraction: dict) -> list[str]:
    errors = []
    if extraction.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {extraction.get('schema')}")
    if extraction.get("source_treated_as_truth"):
        errors.append("source_treated_as_truth must be False")
    if not extraction.get("uncertainty_preserved"):
        errors.append("uncertainty_preserved must be True")
    return errors
