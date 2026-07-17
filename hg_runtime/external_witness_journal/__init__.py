"""External Witness Journal (EWJ) — append-only GitHub hash witness log."""

from hg_runtime.external_witness_journal.agent0_context import (
    EWJ_BOOT_INSTRUCTION,
    answer_journal_status_query,
    build_agent0_witness_journal_context,
)
from hg_runtime.external_witness_journal.schema import (
    WitnessEventClass,
    WitnessImportanceClass,
    WitnessJournalBundle,
)

__all__ = [
    "EWJ_BOOT_INSTRUCTION",
    "WitnessEventClass",
    "WitnessImportanceClass",
    "WitnessJournalBundle",
    "answer_journal_status_query",
    "build_agent0_witness_journal_context",
]
