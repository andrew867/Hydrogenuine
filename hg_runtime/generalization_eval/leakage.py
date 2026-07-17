"""Leakage audits.

Before a held-out result may be green, a leakage audit must confirm the case did
not leak its answer key and did not appear in the training split. A detected leak
blocks green; a missing audit blocks green.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.generalization_eval.schemas import (
    LEAKAGE_AUDIT_SCHEMA,
    GeneralizationEvalError,
    as_list,
    neutral_flags,
    reject_authority_payload,
    require_fields,
    _ANSWER_KEY_KEYS,
)


def audit_leakage(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Produce a leakage audit for a held-out case against its split.

    ``leak_detected`` is true if the case carries an answer key or if the case
    appears in the training refs. The audit is always *recorded*; a leak does not
    silently pass.
    """
    require_fields(payload, ("audit_id", "case_ref", "split_ref"))
    data = dict(payload)
    reject_authority_payload(data)

    reasons: list[str] = []
    case = data.get("case", {})
    if isinstance(case, Mapping):
        for key in case:
            if key in _ANSWER_KEY_KEYS:
                reasons.append(f"answer_key_present:{key}")
    train_refs = set(as_list(data, "train_refs"))
    if data["case_ref"] in train_refs:
        reasons.append("case_in_training_split")

    leak_detected = bool(reasons) or bool(data.get("leak_detected"))
    audit = {
        "schema": LEAKAGE_AUDIT_SCHEMA,
        "audit_id": data["audit_id"],
        "case_ref": data["case_ref"],
        "split_ref": data["split_ref"],
        "leak_detected": leak_detected,
        "reasons": reasons,
        "passed": not leak_detected,
        "recorded": True,
        **neutral_flags(),
    }
    return audit


def require_leakage_audit(audit: Any) -> dict[str, Any]:
    """Refuse a green path with no leakage audit; refuse one whose audit found a leak."""
    if not isinstance(audit, Mapping) or audit.get("schema") != LEAKAGE_AUDIT_SCHEMA:
        raise GeneralizationEvalError("leakage_audit_required_for_heldout_case")
    if audit.get("leak_detected"):
        raise GeneralizationEvalError("answer_key_leakage_blocks_green")
    return dict(audit)


__all__ = ["audit_leakage", "require_leakage_audit"]
