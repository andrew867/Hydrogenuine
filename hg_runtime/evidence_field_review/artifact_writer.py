"""P70 evidence field review artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.evidence_field_review.review import (
    validate_discrepancy,
    validate_evidence_review,
    validate_reproduction_packet,
    validate_reviewer_notes,
    validate_unresolved_gap,
)
from hg_runtime.evidence_field_review.schemas import reject_evidence_overreach


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_evidence_artifacts(
    packets: list[dict],
    reviews: list[dict],
    notes: list[dict],
    discrepancies: list[dict],
    gaps: list[dict],
) -> dict:
    for p in packets:
        reject_evidence_overreach(p)
    v_pk = [{"packet": p, "valid": not validate_reproduction_packet(p), "issues": validate_reproduction_packet(p)} for p in packets]
    v_rv = [{"review": r, "valid": not validate_evidence_review(r), "issues": validate_evidence_review(r)} for r in reviews]
    v_nt = [{"notes": n, "valid": not validate_reviewer_notes(n), "issues": validate_reviewer_notes(n)} for n in notes]
    v_dc = [{"discrepancy": d, "valid": not validate_discrepancy(d), "issues": validate_discrepancy(d)} for d in discrepancies]
    v_gp = [{"gap": g, "valid": not validate_unresolved_gap(g), "issues": validate_unresolved_gap(g)} for g in gaps]
    result = {
        "packets": v_pk, "reviews": v_rv, "notes": v_nt,
        "discrepancies": v_dc, "gaps": v_gp,
        "all_packets_valid": all(v["valid"] for v in v_pk),
        "all_reviews_valid": all(v["valid"] for v in v_rv),
        "all_notes_valid": all(v["valid"] for v in v_nt),
        "all_discrepancies_valid": all(v["valid"] for v in v_dc),
        "all_gaps_valid": all(v["valid"] for v in v_gp),
        "no_truth_claims": all(not r.get("is_truth") for r in reviews),
        "no_authority_claims": all(not n.get("is_authority") for n in notes),
        "discrepancies_preserved": all(d.get("preserved") for d in discrepancies),
        "gaps_preserved": all(g.get("preserved") for g in gaps),
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
