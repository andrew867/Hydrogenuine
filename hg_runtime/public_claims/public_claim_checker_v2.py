"""Public Claim Checker v2 — pattern-based forbidden claim detection with
negation-aware context analysis.

The checker is NOT authority. It is a guard. A claim passing the checker
does NOT make it true. Plausible is NOT true. Passing a check is NOT
proof. Promotion is NEVER allowed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from hg_runtime.public_claims.claim_patterns import FORBIDDEN_AFFIRMATIVE_PATTERNS
from hg_runtime.public_claims.negation_scope import is_negated

SCHEMA_VERSION = "public_claim_checker_v2"

_INVARIANTS = {
    "checker_is_not_authority": True,
    "plausible_is_not_true": True,
    "passing_check_is_not_proof": True,
    "promotion_allowed": False,
    "model_output_treated_as_truth": False,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _receipt_id(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _line_number_at(text: str, index: int) -> int:
    """Return the 1-based line number for a character index."""
    return text[:index].count("\n") + 1


def _context_around(text: str, index: int, pattern_len: int, width: int = 60) -> str:
    """Extract context around a match."""
    start = max(0, index - width)
    end = min(len(text), index + pattern_len + width)
    return text[start:end]


def check_text(text: str, *, source_label: str = "", stop_panic: bool = False) -> dict:
    """Scan text for forbidden affirmative claim patterns.

    For each match, use is_negated() to check context. Returns a receipt.

    The checker is NOT authority. A claim passing the checker does NOT
    make it true. Plausible is NOT true. Passing a check is NOT proof.
    """
    if stop_panic:
        receipt = {
            "schema": SCHEMA_VERSION,
            "source_label": source_label,
            "findings": [],
            "flagged_count": 0,
            "clean": False,
            "operator_review_required": True,
            "blocked": True,
            **_INVARIANTS,
            "checked_at": _utc_now_iso(),
        }
        receipt["receipt_id"] = _receipt_id(receipt)
        return receipt

    lower = text.lower()
    findings = []

    for entry in FORBIDDEN_AFFIRMATIVE_PATTERNS:
        pattern = entry["pattern"]
        category = entry["category"]

        # Find all occurrences
        start = 0
        while True:
            idx = lower.find(pattern, start)
            if idx == -1:
                break

            negated = is_negated(text, idx)
            flagged = not negated

            findings.append({
                "pattern": pattern,
                "category": category,
                "line_number": _line_number_at(text, idx),
                "context": _context_around(text, idx, len(pattern)),
                "negated": negated,
                "flagged": flagged,
            })

            start = idx + 1

    flagged_count = sum(1 for f in findings if f["flagged"])

    receipt = {
        "schema": SCHEMA_VERSION,
        "source_label": source_label,
        "findings": findings,
        "flagged_count": flagged_count,
        "clean": flagged_count == 0,
        "operator_review_required": flagged_count > 0,
        "blocked": False,
        **_INVARIANTS,
        "checked_at": _utc_now_iso(),
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return receipt


def check_report_file(file_path: str, *, stop_panic: bool = False) -> dict:
    """Read a file and check its text for forbidden claims.

    Does NOT read files at import time. Reads only when called.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return check_text(text, source_label=file_path, stop_panic=stop_panic)


def validate_claim_check_receipt(receipt: dict) -> list:
    """Validate a claim check receipt's invariants.

    Returns list of errors (empty = valid).
    """
    errors = []

    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, "
            f"got {receipt.get('schema')}"
        )

    if receipt.get("checker_is_not_authority") is not True:
        errors.append("checker_is_not_authority must be True")

    if receipt.get("plausible_is_not_true") is not True:
        errors.append("plausible_is_not_true must be True")

    if receipt.get("passing_check_is_not_proof") is not True:
        errors.append("passing_check_is_not_proof must be True")

    if receipt.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    if receipt.get("model_output_treated_as_truth") is not False:
        errors.append("model_output_treated_as_truth must be False")

    return errors


def is_safe_for_publication(receipt: dict) -> bool:
    """True only if clean=True and not blocked.

    Safe for publication does NOT mean true. It means the text did not
    trigger forbidden affirmative claim patterns.
    """
    return receipt.get("clean", False) is True and not receipt.get("blocked", False)
