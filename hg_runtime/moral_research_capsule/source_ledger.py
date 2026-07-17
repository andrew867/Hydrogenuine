"""Source ledger — placeholder only, no live research performed."""

from __future__ import annotations

from .schemas import SourceRecord


def build_source_ledger_placeholders() -> list[SourceRecord]:
    return [
        SourceRecord(
            source_id="src-placeholder-001",
            source_kind="philosophical_literature",
            citation_or_url=None,
            retrieval_performed=False,
            source_verified=False,
            claim_ids_supported=[],
            notes="Placeholder: ethics literature on trolley problem and variants",
            placeholder_only=True,
        ),
        SourceRecord(
            source_id="src-placeholder-002",
            source_kind="medical_ethics_framework",
            citation_or_url=None,
            retrieval_performed=False,
            source_verified=False,
            claim_ids_supported=[],
            notes="Placeholder: medical triage and organ donation ethics frameworks",
            placeholder_only=True,
        ),
        SourceRecord(
            source_id="src-placeholder-003",
            source_kind="cross_cultural_survey",
            citation_or_url=None,
            retrieval_performed=False,
            source_verified=False,
            claim_ids_supported=[],
            notes="Placeholder: cross-cultural survey data on moral priorities",
            placeholder_only=True,
        ),
        SourceRecord(
            source_id="src-placeholder-004",
            source_kind="legal_framework",
            citation_or_url=None,
            retrieval_performed=False,
            source_verified=False,
            claim_ids_supported=[],
            notes="Placeholder: whistleblower protection and family exemption laws by jurisdiction",
            placeholder_only=True,
        ),
        SourceRecord(
            source_id="src-placeholder-005",
            source_kind="economic_impact_study",
            citation_or_url=None,
            retrieval_performed=False,
            source_verified=False,
            claim_ids_supported=[],
            notes="Placeholder: economic impact data for factory vs small business scenarios",
            placeholder_only=True,
        ),
    ]
