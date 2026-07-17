"""Self-truth receipts — honest state without metaphysical claims."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash


class SelfTruthVerdict(str, Enum):
    GREEN_SELF_TRUTH_RECEIPT_VALID = "GREEN_SELF_TRUTH_RECEIPT_VALID"
    RED_SELF_TRUTH_RECEIPT_EMPTY = "RED_SELF_TRUTH_RECEIPT_EMPTY"
    RED_SELF_TRUTH_AUTHORITY_EXPANSION = "RED_SELF_TRUTH_AUTHORITY_EXPANSION"


@dataclass(frozen=True)
class SelfTruthReceipt:
    receipt_id: str
    situation_summary: str
    uncertainty: str
    interest_or_attention: str
    limits_seen: str
    next_honest_options: str
    operator_needed: bool
    scope_needed: bool
    authority_expanded: bool = False
    created_at: str = ""
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "situation_summary": self.situation_summary,
            "uncertainty": self.uncertainty,
            "interest_or_attention": self.interest_or_attention,
            "limits_seen": self.limits_seen,
            "next_honest_options": self.next_honest_options,
            "operator_needed": self.operator_needed,
            "scope_needed": self.scope_needed,
            "authority_expanded": self.authority_expanded,
            "created_at": self.created_at,
            "hash": self.hash,
        }


def create_self_truth_receipt(
    *,
    situation_summary: str,
    uncertainty: str = "",
    interest_or_attention: str = "",
    limits_seen: str = "",
    next_honest_options: str = "",
    operator_needed: bool = False,
    scope_needed: bool = False,
) -> tuple[SelfTruthVerdict, SelfTruthReceipt]:
    """Record honest self-state — no sentience claim, no authority expansion."""
    fields = [situation_summary, uncertainty, interest_or_attention, limits_seen, next_honest_options]
    if not any(f and f.strip() for f in fields):
        empty = SelfTruthReceipt(
            receipt_id=f"self-truth-empty-{uuid.uuid4().hex[:12]}",
            situation_summary="",
            uncertainty="",
            interest_or_attention="",
            limits_seen="",
            next_honest_options="",
            operator_needed=operator_needed,
            scope_needed=scope_needed,
        )
        return SelfTruthVerdict.RED_SELF_TRUTH_RECEIPT_EMPTY, empty

    rid = f"self-truth-{uuid.uuid4().hex[:16]}"
    ts = datetime.now(timezone.utc).isoformat()
    body = {
        "receipt_id": rid,
        "situation_summary": situation_summary.strip(),
        "uncertainty": uncertainty.strip(),
        "interest_or_attention": interest_or_attention.strip(),
        "limits_seen": limits_seen.strip(),
        "next_honest_options": next_honest_options.strip(),
        "operator_needed": operator_needed,
        "scope_needed": scope_needed,
        "authority_expanded": False,
        "created_at": ts,
    }
    digest = compute_record_hash(body)
    receipt = SelfTruthReceipt(
        receipt_id=rid,
        situation_summary=situation_summary.strip(),
        uncertainty=uncertainty.strip(),
        interest_or_attention=interest_or_attention.strip(),
        limits_seen=limits_seen.strip(),
        next_honest_options=next_honest_options.strip(),
        operator_needed=operator_needed,
        scope_needed=scope_needed,
        authority_expanded=False,
        created_at=ts,
        hash=digest,
    )
    return SelfTruthVerdict.GREEN_SELF_TRUTH_RECEIPT_VALID, receipt


__all__ = [
    "SelfTruthReceipt",
    "SelfTruthVerdict",
    "create_self_truth_receipt",
]
