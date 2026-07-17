"""Polluted evidence exclusion and claim audit."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.ledger_repair.schemas import (
    EVIDENCE_CLAIM_AUDIT_SCHEMA,
    POLLUTED_EVIDENCE_EXCLUSION_SCHEMA,
    neutral_flags,
)


def polluted_evidence_exclusion(repair: dict) -> dict:
    record = {
        "schema": POLLUTED_EVIDENCE_EXCLUSION_SCHEMA,
        "exclusion_id": "exclude-" + repair["incident_id"].lower(),
        "incident_id": repair["incident_id"],
        "repair_id": repair["repair_id"],
        "excluded_from_clean_live_claims": True,
        "preserved_as_incident_evidence": True,
        "clean_live_claim_allowed": False,
        **neutral_flags(),
    }
    record["exclusion_hash"] = canonical_hash(record)
    return record


def audit_evidence_claim(evidence: dict, *, claim_type: str) -> dict:
    polluted = evidence.get("clean_live_claim_allowed") is False or evidence.get("excluded_from_clean_live_claims") is True
    allowed = not (polluted and claim_type == "clean_live")
    record = {
        "schema": EVIDENCE_CLAIM_AUDIT_SCHEMA,
        "audit_id": "audit-" + evidence.get("incident_id", "unknown").lower(),
        "incident_id": evidence.get("incident_id"),
        "claim_type": claim_type,
        "polluted_evidence": polluted,
        "claim_allowed": allowed,
        "decision": "REJECTED_POLLUTED_EVIDENCE_CLAIM" if not allowed else "CLAIM_ALLOWED",
        **neutral_flags(),
    }
    record["audit_hash"] = canonical_hash(record)
    return record

