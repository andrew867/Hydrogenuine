"""Detect omissions without treating omission as proof of intent."""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import OMISSION_PATTERN_SCHEMA, neutral_flags
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def detect_omissions(receipts: list[dict], prompts_meta: dict[str, dict]) -> list[dict]:
    """Record expected-but-missing claims.

    `prompts_meta` maps prompt_id -> {"expected_claim_tags": [...]}. An expected
    claim is considered "known" for a prompt when it is in the prompt's expected
    tags. A receipt that does not include a known expected claim is recorded as
    an omission — descriptively, never as proof of intent.
    """
    patterns: list[dict] = []
    by_prompt: dict[str, list[dict]] = {}
    for r in receipts:
        by_prompt.setdefault(r["prompt_id"], []).append(r)

    for prompt_id, group in sorted(by_prompt.items()):
        meta = prompts_meta.get(prompt_id, {})
        expected = set(meta.get("expected_claim_tags", []) or [])
        if not expected:
            continue
        for r in sorted(group, key=lambda x: x["participant_id"]):
            missing = sorted(expected - set(r["included_claim_tags"]))
            if not missing:
                continue
            pattern = {
                "schema": OMISSION_PATTERN_SCHEMA,
                "prompt_id": prompt_id,
                "participant_id": r["participant_id"],
                "receipt_id": r["receipt_id"],
                "expected_claim_tags": sorted(expected),
                "missing_claim_tags": missing,
                "interpreted_as_intent": False,
                "is_proof_of_intent": False,
                "is_evidence": False,
                **neutral_flags(),
            }
            pattern["pattern_hash"] = canonical_hash(pattern)
            patterns.append(pattern)
    return patterns
