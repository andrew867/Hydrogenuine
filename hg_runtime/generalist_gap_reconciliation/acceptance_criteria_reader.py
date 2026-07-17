"""P26 acceptance-criteria reader.

The exact P26 specification lives in the outer generalist-runtime index, which is
not present in this workspace. To stay honest, this reader declares a
representative, named set of P26 acceptance criteria derived from the criterion
name ("Persistent Memory / Experience Ledger") and the reconciliation intent in
the master plan, and records that the authoritative outer spec was NOT ingested.
These criteria are an analysis scaffold, not the authoritative P26 spec.
"""

from __future__ import annotations

from hg_runtime.generalist_gap_reconciliation.schemas import assert_neutral, neutral_flags, record_hash

# (criterion id, title, intent).
_CRITERIA = [
    ("P26-AC-1", "Append-only experience ledger with hash chain", "Persist agent experiences as an append-only, hash-chained ledger."),
    ("P26-AC-2", "Provenance-linked memory entries", "Each memory entry carries provenance lineage."),
    ("P26-AC-3", "Deterministic replay of memory state", "Memory state is deterministically replayable from records."),
    ("P26-AC-4", "Retraction/quarantine without erasure", "Memory can be retracted or quarantined while preserving originals."),
    ("P26-AC-5", "Cross-session persistent recall API", "A surface for recalling memory across sessions."),
    ("P26-AC-6", "Experience-to-belief gating with operator review", "Promotion of experience to belief is operator-gated, not automatic."),
    ("P26-AC-7", "Memory decay policy (not erasure)", "Aged memory decays under policy without being erased."),
    ("P26-AC-8", "Unified P26 gate/report/proof", "A single P26-specific gate, report, and proof bundle exists."),
    ("P26-AC-9", "Live autonomous memory writes from agent actions", "Agent actions write to memory autonomously at runtime."),
    ("P26-AC-10", "Self-directed cross-agent memory curation", "Agents autonomously curate/share memory without operator involvement."),
]


def build_acceptance_criterion(*, criterion_id: str, title: str, intent: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "p26_acceptance_criterion_v1",
        "criterion_id": criterion_id,
        "title": title,
        "intent": intent,
        "authoritative_outer_spec_ingested": False,
        "doctrine_note": "Representative scaffold; outer P26 spec not present in workspace.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def read_acceptance_criteria() -> list[dict]:
    return [build_acceptance_criterion(criterion_id=c, title=t, intent=i) for c, t, i in _CRITERIA]
